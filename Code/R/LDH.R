library(tidyverse)
library(gridExtra)

# Load the data and convert the blank and mixed treatments to a uniform format
file_path= "../../Data/Compiled/LDH_ALL_Except_A549.csv"
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
plot_bar_graph <- function(cmpnd, multiple.comparisons = FALSE){
  df_means <-
    df_scaled %>% 
    filter(compound == cmpnd) %>%
    group_by(cells, group, treatment) %>% 
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
  title <- sprintf("LDH Across Groups for SVGp12 - %s", cmpnd)
  plt <- ggplot(data=df_means, mapping = aes(y=response, x=group, fill=treatment), height=10) + 
    geom_bar(position="dodge", stat="identity", width=0.5) + 
    geom_errorbar(aes(ymin=y_err_min, ymax=y_err_max), width=.2, position=position_dodge(.5)) + 
    theme_bw(base_size = 15) + 
    labs(x="", y="LDH (Cell Damage)", fill = "Treatment (μg/ml)", title=title) 
  if (multiple.comparisons){
    for (i in 1:length(groups)){
      grp <- as.character(groups[i])
      
      df_group <- df_scaled %>%
        filter(compound == 'DEP', group == grp)
      
      df_group_means <- df_means %>%
        filter(group == grp)
      
      # Perform the howell_tst for group comparisons
      howell_tst <- games.howell(as.character(df_group$treatment), df_group$response)
      
      # Then oblieterate the statistical power of the test by implementing Šidák familywise correction
      n_comparisons <- nrow(howell_tst)*length(groups)
      alpha_corrected <- 1-(1-0.05)^(1/n_comparisons)
      
      
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
            if (p_val < alpha_corrected) {
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
      
      
      plt <- plt + geom_line(data=df_line, aes(x=x,y=y)) + annotate("text", label=lbl, x=x_text, y=y_text, color="black", size=3)
    }
  }
  
  return(plt)
}

p1 <- plot_bar_graph("DEP")
p2 <- plot_bar_graph("Ox66")
p3 <- plot_bar_graph("DEP + Ox66")

ggsave(p1, filename = "../../Graphs/SVG/LDH//Barplots/DEP.png", device='png', height = 9, width = 16)
ggsave(p2, filename = '../../Graphs/SVG/LDH/Barplots/Ox66.png', device = 'png', height = 9, width = 16)
ggsave(p3, filename = '../../Graphs/SVG/LDH/Barplots/DEP + Ox66.png', device= "png", height = 9, width = 16)

# Fit linear regression and 
plot_and_save <- function(cell_line, cmpnd, assay){
  title <- sprintf("%s Across Groups for %s - %s", assay, cell_line, cmpnd)
  file_path <- sprintf("../../Graphs/SVG/LDH/LinearReg/%s_%s.png", cmpnd, assay)
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
  
  ggsave(file_path, device = "png", width=8, height = 4.5)
}


plot_and_save("DEP", "LDH")
plot_and_save("Ox66", "LDH")
plot_and_save("DEP + Ox66", "LDH")


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


cell_lines <- unique(df_scaled$cells)



plot_ces <- function(cmpnd, assay){
  y_lines <- vector()
  y_pvals <- vector()
  x_lines <- vector()
  x_pvals <- vector()
  
  df_slopes <- 
    df_scaled %>% 
    group_by(cells, compound, group) %>% 
    summarise(slope = find_mdl_coefficient(treatment, response),
              slope_err = find_mdl_coefficient_ce(treatment,response)) %>% 
    mutate(slope_min = slope-slope_err, slope_max=slope+slope_err) 

  df_slopes_cmpnd <-
    df_slopes %>% 
    filter(compound== cmpnd) %>% 
    mutate(group = factor(group, levels = c("Normoxia - 24 Hours", "Hypoxia - 24 Hours",
                                            "Normoxia - 48 Hours", "Hypoxia - 48 Hours"))) %>% 
    arrange(cells, group)
  
  view(df_slopes_cmpnd)
  
  #Calculate the z score for the different between hypoxia and normoxia at 24 hours
  twentyfour.dif.z <- 
    df_slopes_cmpnd %>% 
    filter(group == 'Normoxia - 24 Hours' | group == 'Hypoxia - 24 Hours') %>% 
    group_by(cells) %>% 
    summarise(z_val = diff(slope) / sqrt(sum(slope_err^2)), pval_x = mean(slope)) %>% 
    ungroup
  
  view(twentyfour.dif.z)
  break
  #Calculate the p-vale for that score
  twentyfour.df.p <- pnorm(abs(twentyfour.dif.z$z_val), lower.tail = FALSE) * 2
  
  
  #Calculate the z score for the different between hypoxia and normoxia at 48 hours
  fortyeight.dif.z <- 
    df_slopes_cmpnd %>% 
    filter(group == 'Normoxia - 48 Hours' | group == 'Hypoxia - 48 Hours') %>%
    summarise(z_val = diff(slope) / sqrt(sum(slope_err^2)), pval_x = mean(slope))
  
  
  #Calculate the p-vale for that score
  fortyeight.df.p <- pnorm(abs(fortyeight.dif.z$z_val), lower.tail = FALSE) * 2
  
  
  title <- sprintf("Slope Confidence Intervals for %s - %s (%s)", cell_line, cmpnd, assay)
  dir <= sprintf("../../Graphs/%s/SlopesCEs")
  dir.create(dir, showWarnings = FALSE)
  file_name <- sprintf("%s/%s_%s_%s_CE.png", dir, cell_line, cmpnd, assay)
  
  y_lines <- c(rbind(df_slopes_cmpnd$slope_min, df_slopes_cmpnd$slope_max))
  y_pvals <- rep(c(twentyfour.dif.z$pval_x, twentyfour.dif.z$pval_x,
                   fortyeight.dif.z$pval_x, fortyeight.dif.z$pval_x), each=2)
  
  x_lines <- rep((seq(from = nrow(df_slopes_cmpnd), to = 1, by=-1)/2) + i - 1, each=2)
  x_pvals <- rep((c(3.5,1.5)/2) + i-1, each=4)

  y_dots <- rep(df_slopes_cmpnd$slope, each=2)
  
  lbls <- rep(round(as.numeric(c(twentyfour.df.p, twentyfour.df.p, fortyeight.df.p, fortyeight.df.p)), digits = 5), each=2)
  lbls <- lapply(lbls, function(x){
    if (x < 0.05){
      return (sprintf("p = %s *", x))
    } else{
      return (sprintf("p = %s", x))
    }
  })
  group <- rep(df_slopes_cmpnd$group, each = 2)
  df_lines <- 
    data.frame(x=x_lines, y=y_lines, group=group) 
  plt <-
    ggplot(data=df_lines, mapping=aes(x=x_lines, y=y_lines, color=group)) + 
    geom_line() + 
    geom_text(aes(x=x_pvals, y=y_pvals, label=lbls),color='black') +
    geom_point(x=x_dots, color="black") +
    labs(x="Regression Slopes 95% Confidence Intervals", y="", color="Condition - Exposure Time",
         title=title) +
    theme_bw() +
    theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          panel.grid.major = element_blank(), panel.grid.minor = element_blank()) 
  print(plt)
  #ggsave(file_name, device = "png", height=3)

  
}

plot_ces("DEP", "LDH")
#plot_ces("Ox66", "LDH")
#plot_ces("DEP + Ox66", "LDH")


find_mdl_coefficient_ce <- function(x,y){
  lin_mod <- lm(y~x)
  std_err <- coef(summary(lin_mod))[2,2]
  df <- length(residuals(lin_mod))
  crit_t <- abs(qt(0.05/2, df))
  c(std_err, crit_t * std_err)
}

compare_coefs <- function(condition, exposure_time, corner_title){
  grp<- paste(condition, "_", exposure_time, sep="")
  grp <- sprintf('%s - %s', condition, exposure_time)
  title <- sprintf("%s - Comparison of Additive Slopes for SVGp12 - %s at %s", corner_title, exposure_time, condition)
  file_path <- sprintf("../../Graphs/SVG/LDH/SlopesCEs/Compare_%s_%s.png", exposure_time,condition)
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
  coef.difference <- as.character(signif(abs(coef.combined - coef.dep.ox66), digits=3))
  
  x_lines <-
    c(coef.combined - 1.96*se.combined, coef.combined + 1.96*se.combined,
      coef.dep.ox66 - 1.96*se.dep.ox66, coef.dep.ox66 + 1.96*se.dep.ox66)
  y_lines <- c(1.5,1.5,1,1)
  groups <- c("Combined Calculated", "Combined Calculated", "Combined Experimental", "Combined Experimental")
  
  df_lines2 <- data.frame(x=x_lines, y=y_lines, group = groups) 
    
    plt <- 
    ggplot(data=,df_lines2, mapping= aes(x=x, y=y, color=group)) +
    geom_line(aes(group=group)) +
    annotate("text", x=(coef.combined+ coef.dep.ox66)/2, y = 1.25, label=sprintf("Difference = %s", coef.difference), color="black", size=5) +
    theme_bw(base_size = 10) +
    theme(axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          panel.grid.major = element_blank(), panel.grid.minor = element_blank()) +
    geom_point(aes(x=c(coef.combined, coef.combined, coef.dep.ox66, coef.dep.ox66), y=c(1.5,1.5,1,1), color=group)) +
    ylim(1,1.5) +
    labs(title = title, x="Regression Slopes 95% Confidence Intervals", y="", color="Group") 
    
    return(plt)
  
  
  ggsave(file_path, device = 'png', height=2, width=5)
}

p1 <- compare_coefs("Normoxia", "24 Hours", "A")
p2 <-compare_coefs("Normoxia", "48 Hours", "B")
p3 <- compare_coefs("Hypoxia", "24 Hours", "C")
p4 <- compare_coefs("Hypoxia", "48 Hours", "D")

g <- arrangeGrob(p1,p2,p3,p4, nrow = 2)

ggsave(g, filename = "../../Graphs/SVG/LDH/SlopesCEs/mixture_effects.png", device='png')




