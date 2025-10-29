# Project KAYAK

## Create the env
```bash
$ pwd
Project_02_Kayak

$ alias conda-init='source ~/miniconda3/etc/profile.d/conda.sh'
$ conda-init

$ conda env create --file env_kayak.yml
```

## Activate kayak env
Enregistrer l'env pour le kernel de Jupyter
```bash
$ conda activate kayak

$ python -m ipykernel install --user --name kayak --display-name "KAYAK project"
```

## Install playwright browser

```bash
$ playwright install chromium
```
Failed to install browsers
Error: ERROR: Playwright does not support chromium on ubuntu18.04-x64

