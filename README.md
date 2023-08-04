# Linkedin EasyApply Bot
Automate the application process on LinkedIn

Medium Write-up: https://medium.com/xplor8/how-to-apply-for-1-000-jobs-while-you-are-sleeping-da27edc3b703
Video: https://www.youtube.com/watch?v=4R4E304fEAs

## Setup 

Python 3.10 using a conda virtual environment on Linux (Ubuntu)

The run the bot install requirements
```bash
sudo apt update \
&& sudo apt upgrade \
&& sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev 
```  

```bash
curl https://pyenv.run | bash || echo "pyenv indirilemedi"
```

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
echo 'eval "$(pyenv init -)"' >> ~/.profile

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo 'eval "$(pyenv init -)"' >> ~/.bash_profile

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```  

```bash
pyenv install 3.11 
```  
```bash
pyenv virtualenv 3.11 dev
```  
```bash
pyenv activate dev 
```  
```bash
pip3 install -r requirements.txt
```

Enter your username, password, and search settings into the `config.yaml` file

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

### Uploads

There is no limit to the number of files you can list in the uploads section. 
The program takes the titles from the input boxes and tries to match them with 
list in the config file.

## Execute

To execute the bot run the following in your terminal
```
python3 easyapplybot.py
```

