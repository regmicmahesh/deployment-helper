#!/bin/bash


PROJECT_PATH=$(dirname $(dirname "$(realpath "$0")"))
ENV_FILE_PATH=${PROJECT_PATH}/.env

# Make sure .env exists.
if [[ ! -f ${ENV_FILE_PATH} ]]; then
  echo ".env file not found!"
  exit
fi


# Remove out all the comments and export it.
export $(grep -v '^#' "$ENV_FILE_PATH" | xargs)



echo "Loaded Variables:"
grep -v '^#' $ENV_FILE_PATH | cut -d= -f1 | xargs echo " >"
