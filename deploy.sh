#!/bin/bash

# Auto set execute permission if not yet
if [ ! -x "$0" ]; then
    echo ">>> Give permission for $0"
    chmod +x "$0"
fi
VENV_DIR="venv"

echo ">>> Pull latest code from Git..."
git pull origin master || { echo "Git pull failed"; exit 1; }

echo ">>> Activate virtual environment..."
source "$VENV_DIR/bin/activate" || { echo "Cannot venv tại $VENV_DIR"; exit 1; }

echo ">>> Install required libraries..."
pip install -r requirements.txt || { echo "Install required libraries failed"; exit 1; }

echo ">>> Reload + restart service chatbot..."
sudo systemctl daemon-reload
sudo systemctl restart chatbot.service

echo ">>> Status chatbot.service:"
sudo systemctl status chatbot.service

# Revert local change to script
sudo git checkout -- "$0"

# if you want to run the chatbot service in the background, uncomment the line below
# sudo cp sale_advisor_deploy.sh /SaleAdvisor/deploy.sh