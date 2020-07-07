# install.packages(c("httr", "jsonlite","glue", "knitr", "base64enc"))
# install.packages("tidyverse")

library(tidyverse)
library(base64enc)
library(glue)
library(jsonlite)
library(httr)
library(plyr)


server_url <- "http://127.0.0.1:8001/" # change this to match your environment

post_data = '{
                  "data": {
              "type": "token",
              "attributes": {
              "username": "karyn",
              "password": "specialP@55word"
              }
              }
              }'

# GET the auth token from the /token/ endpoint
req <- httr::POST(glue("{server_url}token/"),
                  httr::add_headers(
                    "Content-Type" = "application/vnd.api+json"
                  ),
                  body = post_data,
                  encode = "json"
);

#Extract the access token from the response
token <- paste("Bearer", httr::content(req, type="application/json", as="parsed", encoding="UTF-8")$token)

# Fetch the images rom remote URLs and encode them as base64

pic1 <- base64enc::base64encode("https://www.flowbee.com/images/RickH.jpg")
pic2 <- base64enc::base64encode('https://chia.com/wp-content/uploads/2019/07/Clapper-Box-and-Unit-HI-300x300.jpg')


# An example data frame of products
prods = data.frame(
  name=c("Flowbee",
          "The Clapper"),
  upc=sample(100000:999999,2), # using random UPCs for this example
  url=c("https://www.flowbee.com",
        "https://www.walmart.com/ip/The-Clapper-Wireless-Sound-Activated-Switch-with-Clap-Detection-As-Seen-on-TV/10740655"
        ),
  manufacturer=c("Flowbee, Inc.",
                 "Clappercorp"),
  color=c("yellow",
          "white"),
  brand=c("Flowbee","Clapper"),
  size=c("small","small"),
  short_description=c("",""),
  long_description=c("",""),
  image=c(pic1, 
          pic2),
  datadoc = c(155324, 
              155324)
)


# Use a combination of toJSON() and glue() to assemble the json payload
field_list <- c(
              "name",
              "upc",
              "url",
              "manufacturer",
              "color",
              "brand",
              "size",
              "short_description",
              "long_description"
               , "image"
            )

prods$attribute_json <-
  adply(
    prods[, field_list],
    .margins = 1,
    .fun = toJSON,
    auto_unbox = TRUE
    #,pretty = TRUE
  ) %>% select(V1)

prods[1,"attribute_json"] 
  
# the attribute JSON object has brackets around it that need to be removed (the auto_unbox above doesn't work)
# with a grepl() and eval(parse())
prods = prods %>% mutate( attribute_txt = 
                            eval(parse(text = 
                            gsub(
                              "\\[|\\]",
                              "", 
                              as.character(attribute_json) 
                                 ) 
                            ))
                          )
prods[1,"attribute_txt"] 
                 
# Build the full payload string           
# glue() uses double braces for literal braces
put_payloads <- prods %>% mutate(
              prod_data = 
              glue('{{
                    "data": {{
                      "attributes": 
                        { attribute_txt  }  
                      ,
                      "relationships": {{
                      "dataDocuments": {{"data": [{{"type": "dataDocument", "id": {datadoc} }}]}
                      }},
                      "type": "product"
                      }}
                      }}')
) %>% select(prod_data)

# The put_payloads data frame can now be iterated over, making a separate call for each record

#Actual API calls
url <- glue("{server_url}products")

headers <- add_headers('Authorization' = token)

for (row in 1:nrow(put_payloads)) {
  payload = put_payloads[row,"prod_data"]
  req <- httr::POST(url, body=payload, headers ,content_type("application/vnd.api+json") , encoding="UTF-8")
  json <- httr::content(req, as = "text")
  print(json)
}



