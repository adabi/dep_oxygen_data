library(tidyverse)
file_path= "../../Data/Compiled/SVG_LDH_ALL.csv"
df <- read.csv(file_path)

# replace blanks with 0 ug/ml and split the treatment into numbers and units
df <- 
  df %>% 
  mutate(treatment = str_replace(treatment, "Blank", "0 ug/ml"))  %>% 
  separate(treatment, into=c("treatment", "units"), sep=" ") %>% 
  mutate(treatment = as.numeric(treatment))

# Scale all the values to the blank(treatment = 0) in every condition at every exposure time for every compound
scaling_lst <- 
  df %>% 
  unite(cond_ex, condition, exposure_time, sep="_") %>% 
  unite(group, compound, cond_ex, sep=",") %>% 
  split(.$group)


df_scaled <- 
  lapply(names(scaling_lst), function(x){
    blank_mean <- 
      scaling_lst[[x]] %>% 
      filter(group == x, treatment ==0) %>% 
      select(response) %>% 
      pull %>% 
      mean
    
    scaling_lst[[x]] %>% 
      mutate(response = response / blank_mean)
  }) %>% 
  bind_rows() %>% 
  separate(group, into=c("compound", "group"), sep=",")


#Plot the linear regression for DEP

df_scaled %>%
  filter(compound=="DEP") %>%
  mutate(group = factor(group, levels = c("Normoxia_24 Hours", "Hypoxia_24 Hours",
                                            "Normoxia_48 Hours", "Hypoxia_48 Hours"))) %>% 
  ggplot(mapping=aes(x=treatment, y=response, color=group)) +
  geom_jitter(width=0.3, alpha= 0.5) +
  stat_smooth(method="lm", se=FALSE) +
  labs(title= "DEP - Scaled LDH for Human Astroglial Cells (SVGp12)",
       x="Treatment (μg/ml)", y="LDH (Cell Leakage)", 
       color="Condition_Exposure Time")
ggsave("../../Graphs/SVG/SVG_DEP_LDH_Scaled.png", device = "png", type = "cairo", width=6)

#Plot the linear regression for Ox66
df_scaled %>%
  filter(compound=="Ox66") %>%
  mutate(group = factor(group, levels = c("Normoxia_24 Hours", "Hypoxia_24 Hours",
                                          "Normoxia_48 Hours", "Hypoxia_48 Hours"))) %>% 
  ggplot(mapping=aes(x=treatment, y=response, color=group), width=18) +
  geom_jitter(width=0.3, alpha= 0.5) +
  stat_smooth(method="lm", se=FALSE) +
  labs(title= "Ox66 - Scaled LDH for Human Astroglial Cells (SVGp12)",
       x="Treatment (μg/ml)", y="LDH (Cell Leakage)", 
       color="Condition_Exposure Time")

ggsave("../../Graphs/SVG/SVG_Ox66_LDH_Scaled.png", device = "png", type = "cairo", width=6)



lin <- df_scaled %>% 
  filter(compound == "DEP", exposure_time=="48 Hours", condition == "Normoxia") %>% 
  lm(data=., log(response)~treatment)

lnr_mdl <-
  df_scaled %>% 
  filter(compound=="DEP", exposure_time=="48 Hours") %>% 
  lm(data=., log(response)~treatment*condition)

summary(lin)
summary(lnr_mdl)