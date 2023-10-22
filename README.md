# Linkedin EasyApply Bot
Automate the application process on LinkedIn

Medium Write-up: https://medium.com/xplor8/how-to-apply-for-1-000-jobs-while-you-are-sleeping-da27edc3b703
Video: https://www.youtube.com/watch?v=4R4E304fEAs

## Setup 


### 1. Enter your username, password, and search settings into the `config.yaml` file

```yaml
username: # Insert your username here
password: # Insert your password here

positions:
- # positions you want to search for
- # Another position you want to search for
- # A third position you want to search for

locations:
- # Location you want to search for
- # A second location you want to search in 

uploads:
 Resume: # PATH TO Resume 
 Cover Letter: # PATH TO cover letter
 Photo: # PATH TO photo
# Note file_key:file_paths contained inside the uploads section should be writted without a dash ('-') 

output_filename:
- # PATH TO OUTPUT FILE (default output.csv)

blacklist:
- # Company names you want to ignore
```
__NOTE: AFTER EDITING SAVE FILE, DO NOT COMMIT FILE__

#### Uploads

There is no limit to the number of files you can list in the uploads section. 
The program takes the titles from the input boxes and tries to match them with 
list in the config file.

### 2. Install Docker  

Please Check This [Page](https://docs.docker.com/engine/install/)  

### 3. Execute The docker compose  

From the terminal or git bash or power shell, go the project folder and run below command  
`docker compose up -d --build`  

### 4. See The Run

Open your browser and go to the 
 - http://localhost:7900/

 And see the results. 
 It will run whenever your computer runs. Have a good luck. 
 