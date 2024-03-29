

# Define the Games-Howell function to carry out the test for group comparisons
games.howell <- function(grp, obs) {
  
  #Create combinations
  combs <- combn(unique(grp), 2)
  
  # Statistics that will be used throughout the calculations:
  # n = sample size of each group
  # groups = number of groups in data
  # Mean = means of each group sample
  # std = variance of each group sample
  n <- tapply(obs, grp, length)
  groups <- length(tapply(obs, grp, length))
  Mean <- tapply(obs, grp, mean)
  std <- tapply(obs, grp, var)
  
  statistics <- lapply(1:ncol(combs), function(x) {
    
    mean.diff <- Mean[combs[2,x]] - Mean[combs[1,x]]
    
    #t-values
    t <- abs(Mean[combs[1,x]] - Mean[combs[2,x]]) / sqrt((std[combs[1,x]] / n[combs[1,x]]) + (std[combs[2,x]] / n[combs[2,x]]))
    
    # Degrees of Freedom
    df <- (std[combs[1,x]] / n[combs[1,x]] + std[combs[2,x]] / n[combs[2,x]])^2 / # Numerator Degrees of Freedom
      ((std[combs[1,x]] / n[combs[1,x]])^2 / (n[combs[1,x]] - 1) + # Part 1 of Denominator Degrees of Freedom 
         (std[combs[2,x]] / n[combs[2,x]])^2 / (n[combs[2,x]] - 1)) # Part 2 of Denominator Degrees of Freedom
    
    #p-values
    p <- ptukey(t * sqrt(2), groups, df, lower.tail = FALSE)
    
    # Sigma standard error
    se <- sqrt(0.5 * (std[combs[1,x]] / n[combs[1,x]] + std[combs[2,x]] / n[combs[2,x]]))
    
    # Upper Confidence Limit
    upper.conf <- lapply(1:ncol(combs), function(x) {
      mean.diff + qtukey(p = 0.95, nmeans = groups, df = df) * se
    })[[1]]
    
    # Lower Confidence Limit
    lower.conf <- lapply(1:ncol(combs), function(x) {
      mean.diff - qtukey(p = 0.95, nmeans = groups, df = df) * se
    })[[1]]
    
    # Group Combinations
    grp.comb <- paste(combs[1,x], ':', combs[2,x])
    
    # Collect all statistics into list
    stats <- list(grp.comb, mean.diff, se, t, df, p, upper.conf, lower.conf)
  })
  
  # Unlist statistics collected earlier
  stats.unlisted <- lapply(statistics, function(x) {
    unlist(x)
  })
  
  # Create dataframe from flattened list
  results <- data.frame(matrix(unlist(stats.unlisted), nrow = length(stats.unlisted), byrow=TRUE))
  
  # Select columns set as factors that should be numeric and change with as.numeric
  results[c(2, 3:ncol(results))] <- round(as.numeric(as.matrix(results[c(2, 3:ncol(results))])), digits = 3)
  
  # Rename data frame columns
  colnames(results) <- c('groups', 'Mean Difference', 'Standard Error', 't', 'df', 'p', 'upper limit', 'lower limit')
  
  return(results)
}

library(tidyverse)
library(gridExtra)

# Load the data and convert the blank and mixed treatments to a uniform format
file_path= "../../Data/Compiled/SVG_LDH_ALL.csv"
df <- read.csv(file_path)
df <- 
  df %>% 
  mutate(treatment = str_replace(treatment, "Blank", "0 ug/ml"),
         treatment = str_replace(treatment, "20 ug/ml \\+ 50 ppm", "70 ug/ml"),
         treatment = str_replace(treatment, "50 ug/ml \\+ 100 ppm", "150 ug/ml"),
         treatment = str_replace(treatment, "100 ug/ml \\+ 200 ppm", "300 ug/ml")) %>% 
  separate(treatment, into=c("treatment", "units"), sep=" ") %>% 
  mutate(treatment = as.numeric(treatment)) %>% 
  select(-units) %>% 
  unite(group, condition, exposure_time, sep=" - ")

df_scaled <- df


#Barplot galore. Print barplots by group and create significance brackets using the games-howell test

df_means <-
  df_scaled %>% 
  filter(compound == 'DEP') %>%
  group_by(group, treatment) %>% 
  summarise(err = sd(response)/sqrt(length(response)), response=mean(response)) %>% 
  ungroup %>% 
  mutate(treatment = factor(treatment)) %>% 
  mutate(group = factor(group, levels=c('Normoxia - 24 Hours', 'Hypoxia - 24 Hours', 
                                        'Normoxia - 48 Hours', 'Hypoxia - 48 Hours'))) %>% 
  arrange(group, treatment)





df_means$y_err_max <- df_means$response + df_means$err
df_means$y_err_min <- df_means$response - df_means$err
max_height = max(df_means$y_err_max)
unit <- max_height / 25
bar_width = 0.5/3

groups <- unique(as.character(df_means$group))
treatments <- unique(as.character(df_means$treatment))

plt <- ggplot(data=df_means, mapping = aes(y=response, x=group, fill=treatment), height=10) + 
  geom_bar(position="dodge", stat="identity", width=0.5) + 
  geom_errorbar(aes(ymin=y_err_min, ymax=y_err_max), width=.2, position=position_dodge(.5)) + 
  theme_bw(base_size = 11) + 
  labs(x="", y="LDH (Cell Damage)", fill = "Treatment (μg/ml)", title="LDH Across Groups for SVGp12 - DEP") 

for (i in 1:length(groups)){
  grp <- as.character(groups[i])
  
  df_group <- df_scaled %>% 
    filter(compound == 'DEP', group == grp)
  
  df_group_means <- df_means %>% 
    filter(group == grp)
  
  howell_tst <- games.howell(as.character(df_group$treatment), df_group$response)
  
  group_starting_x <- i - (length(treatments) * bar_width)/2
  x_values = list()
  y_offset <- 0
  highest_treatment_in_group <- max(df_group_means$y_err_max)
  for (j in 1:(length(treatments) -1)){
    for (k in (j + 1):length(treatments)){
      
      max_treatment_height <-
        df_group_means %>% 
        filter(treatment == treatments[j] | treatment == treatments[k]) %>% 
        select(y_err_max) %>% 
        pull %>% 
        max
      
      x_values <- c(group_starting_x + j*bar_width - bar_width/2 + bar_width/10, 
                    group_starting_x + j*bar_width - bar_width/2 + bar_width/10, 
                    group_starting_x + k*bar_width - bar_width/2 - bar_width/10, 
                    group_starting_x + k*bar_width - bar_width/2 - bar_width/10)
      
      
      if (k-j ==1) {
        y_pos <- max_treatment_height + 2 * unit
      } else {
        y_pos <- highest_treatment_in_group + 2*unit*(j - 1 + k - 1) 
      }
      
      y_values <- c(y_pos-unit, y_pos, y_pos, y_pos-unit)
      x_text <- (group_starting_x + j*bar_width - bar_width/2 + bar_width/10 + group_starting_x + k*bar_width - bar_width/2 - bar_width/10)/2
      y_text <- y_pos + 0.75*unit
      df_line <- data.frame(x=x_values,y=y_values, treatment = rep(c('0'), 2))
      treatments_conc <- paste(treatments[j], treatments[k], sep=" : ")
      p_val <- 
        howell_tst %>% 
        filter(groups == treatments_conc) %>% 
        select(p) %>% 
        pull 
      
      # A length check since R seems to insist that some of the p values be stored as numeric(0), producing a NULL as the output of the if statement. YAY R!
      if (length(p_val) != 0){
        if (p_val < 0.05) {
          lbl <- "*"
        } else {
          lbl <- "n.s."
        }
      } else {
        lbl <- "n.s."
      }
      
      plt <- plt + geom_line(data=df_line, aes(x=x,y=y)) + annotate("text", label=lbl, x=x_text, y=y_text, color="black", size=3)
    }
  }
}

print(plt)
```


```{r}
# Fit linear regression and 
plot_and_save <- function(cmpnd, assay){
  title <- sprintf("LDH Across Groups for Human Astroglial Cells (SVGp12) - %s", assay, cmpnd)
  file_path <- sprintf("../../Graphs/SVG/%s_%s.png", cmpnd, assay)
  df_scaled %>%
    filter(compound==cmpnd) %>%
    mutate(group = factor(group, levels = c("Normoxia - 24 Hours", "Hypoxia - 24 Hours",
                                            "Normoxia - 48 Hours", "Hypoxia - 48 Hours"))) %>% 
    arrange(group) %>% 
    ggplot(mapping=aes(x=treatment, y=response, color=group)) +
    geom_jitter(width=0.3, alpha= 0.5) +
    stat_smooth(method="lm", se=FALSE) +
    labs(title= title,
         x="Treatment (μg/ml)", y="LDH (Cell Leakage)", 
         color="Condition - Exposure Time") +
    theme_bw(base_size= 10)
  
  ggsave(file_path, device = "png", width=8, type="cairo", height = 4.5)
}


p1<- plot_and_save("DEP", "LDH")
p2<- plot_and_save("Ox66", "LDH")
p3<- plot_and_save("DEP + Ox66", "LDH")

#g <- arrangeGrob(p1,p2,p3, nrow = 3)

#ggsave("../../Graphs/compiled_trends.png", g, device="png", type="cairo")

```


```{r}
#Function for finding the slope coefficient 
find_mdl_coefficient <- function(x,y){
  coef(summary(lm(y~x)))[2,1]
}

#Function for finding the slope coefficient confidence interval
find_mdl_coefficient_ce <- function(x,y){
  lin_mod <- lm(y~x)
  std_err <- coef(summary(lin_mod))[2,2]
  df <- length(residuals(lin_mod))
  crit_t <- abs(qt(0.05/2, df))
  (crit_t * std_err)
}

plot_ces <- function(cmpnd, assay){
  df_slopes <- 
    df_scaled %>% 
    group_by(compound, group) %>% 
    summarise(slope = find_mdl_coefficient(treatment, response),
              slope_err = find_mdl_coefficient_ce(treatment,response)) %>% 
    mutate(slope_min = slope-slope_err, slope_max=slope+slope_err) 
  
  df_slopes_dep <-
    df_slopes %>% 
    filter(compound== cmpnd) %>% 
    mutate(group = factor(group, levels = c("Normoxia - 24 Hours", "Hypoxia - 24 Hours",
                                            "Normoxia - 48 Hours", "Hypoxia - 48 Hours"))) %>% 
    arrange(group)
  
  title <- sprintf("Slope Confidence Intervals for SVGp12 - %s (%s)", cmpnd, assay)
  file_name <- sprintf("../../Graphs/SVG/SVG_%s_%s_CE.png", cmpnd, assay)
  x_lines <- c(rbind(df_slopes_dep$slope_min, df_slopes_dep$slope_max))
  y_lines <- rep(seq(from = nrow(df_slopes_dep), to = 1, by=-1)/2, each=2)
  x_dots <- rep(df_slopes_dep$slope, each=2)
  group <- rep(df_slopes_dep$group, each = 2)
  df_lines <- 
    data.frame(x=x_lines, y=y_lines, group=group) 
  
  ggplot(data=df_lines, mapping=aes(x=x_lines, y=y_lines, color=group)) + 
    geom_line() + 
    geom_point(x=x_dots, color="black") +
    labs(x="Regression Slopes 95% Confidence Intervals", y="", color="Condition_Exposure Time",
         title=title) +
    theme_bw() +
    theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          panel.grid.major = element_blank(), panel.grid.minor = element_blank()) 
  
  ggsave(file_name, device = "png", height=3)
  
}

plot_ces("DEP", "LDH")
plot_ces("Ox66", "LDH")
plot_ces("DEP + Ox66", "LDH")
```


```{r}
find_mdl_coefficient_ce <- function(x,y){
  lin_mod <- lm(y~x)
  std_err <- coef(summary(lin_mod))[2,2]
  df <- length(residuals(lin_mod))
  crit_t <- abs(qt(0.05/2, df))
  c(std_err, crit_t * std_err)
}

compare_coefs <- function(condition, exposure_time){
  grp<- paste(condition, "_", exposure_time, sep="")
  grp <- sprintf('%s - %s', condition, exposure_time)
  title <- sprintf("Comparison of Additive Slopes for SVGp12 - %s at %s", exposure_time, condition)
  file_path <- sprintf("../../Graphs/SVG/compare_%s_%s.png", exposure_time,condition)
  ox66_df <- df_scaled %>% 
    filter(compound == "Ox66", group==grp) 
  
  coef.ox66 <-  find_mdl_coefficient(ox66_df$treatment, ox66_df$response)
  se.ox66 <- find_mdl_coefficient_ce(ox66_df$treatment, ox66_df$response)[1]
  
  
  dep_df <- 
    df_scaled %>% 
    filter(compound == "DEP", group==grp) 
  
  coef.dep <-  find_mdl_coefficient(dep_df$treatment, dep_df$response)
  se.dep <- find_mdl_coefficient_ce(dep_df$treatment, dep_df$response)[1]
  
  response.ox66 <- 
    df_scaled %>% 
    filter(compound == "Ox66", group==grp) %>% 
    group_by(treatment) %>% 
    summarise(response = mean(response)) %>% 
    select(response) %>% 
    pull
  
  response.dep <-
    df_scaled %>%
    filter(compound == "DEP", group==grp) %>% 
    group_by(treatment) %>% 
    summarise(response = mean(response)) %>% 
    select(response) %>% 
    pull
  
  dep_ox66_df <- df_scaled %>% 
    filter(compound == "DEP + Ox66", group==grp) 
  coef.dep.ox66 <-  find_mdl_coefficient(dep_ox66_df$treatment, dep_ox66_df$response)
  se.dep.ox66 <- find_mdl_coefficient_ce(dep_ox66_df$treatment, dep_ox66_df$response)[1]
  
  se.combined <- sqrt((se.dep)^2 + (se.ox66)^2)
  coef.combined <- coef.ox66 + coef.dep
  
  x_lines <-
    c(coef.combined - 1.96*se.combined, coef.combined + 1.96*se.combined,
      coef.dep.ox66 - 1.96*se.dep.ox66, coef.dep.ox66 + 1.96*se.dep.ox66)
  y_lines <- c(1.5,1.5,1,1)
  groups <- c("Combined Calculated", "Combined Calculated", "Combined Experimental", "Combined Experimental")
  
  df_lines2 <- data.frame(x=x_lines, y=y_lines, group = groups) %>% 
    
    ggplot(data=,df_lines2, mapping= aes(x=x, y=y, color=group)) +
    geom_line(aes(group=group)) +
    theme_bw(base_size = 5) +
    theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          panel.grid.major = element_blank(), panel.grid.minor = element_blank()) +
    geom_point(aes(x=c(coef.combined, coef.combined, coef.dep.ox66, coef.dep.ox66), y=c(1.5,1.5,1,1), color=group)) +
    ylim(1,1.5) +
    labs(title = title, x="Regression Slopes 95% Confidence Intervals", y="", color="Group") 
  
  
  ggsave(file_path, device = 'png', height=2, width=5)
}

compare_coefs("Normoxia", "24 Hours")
compare_coefs("Normoxia", "48 Hours")
compare_coefs("Hypoxia", "24 Hours")
compare_coefs("Hypoxia", "48 Hours")

```


