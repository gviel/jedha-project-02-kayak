# Accès AWS (IAM) — Kayak

Le pipeline Kayak écrit et lit des fichiers CSV dans S3. Il utilise **sa propre clé AWS**, rattachée à un
user IAM dont les droits sont limités à ce que le code fait réellement. Aucun `AmazonS3FullAccess`,
aucune clé partagée avec un autre projet.

Pourquoi : une clé AWS d'un autre projet de ce compte a fuité dans un dépôt GitHub public (sortie d'un
notebook qui affichait `os.environ`) et a dû être révoquée. Chaque projet a depuis son user IAM dédié, pour
qu'une fuite n'ouvre que les données de ce projet.

## Qui utilise quoi

| User IAM | Bucket | Préfixe | Fichier local |
|---|---|---|---|
| `kayak` | `cdsd-kayak-datalake` | `csv/` | `.env` (variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`) |

Région : `eu-west-3`. D'après le code, seuls deux scripts accèdent à S3 :

| Script | Opération S3 | Droit requis |
|---|---|---|
| `src/load_csv_to_s3.py` | dépose `csv/cities.csv` et `csv/<YYYYMMDD>/*.csv` (`upload_file`) | `s3:PutObject` |
| `src/load_to_db.py` | liste le préfixe (`list_objects_v2`, paginé) puis lit les fichiers (`get_object`) | `s3:ListBucket` (préfixe `csv/`) + `s3:GetObject` |

L'application Streamlit lit la base PostgreSQL (Neon), pas S3 : elle n'a pas besoin de clé AWS.

Hors périmètre : `src/rds_postgresql_full.py` pilote EC2 et RDS (`boto3.client("ec2")`, `("rds")`). La clé
`kayak` n'a volontairement **aucun** droit sur ces services : lancer ce script avec un profil administrateur
(`AWS_PROFILE=<admin>`), jamais avec la clé du `.env`.

## Policy du user (inline `kayak-datalake-rw`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CsvReadWrite",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::cdsd-kayak-datalake/csv/*"
    },
    {
      "Sid": "ListCsvPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::cdsd-kayak-datalake",
      "Condition": {
        "StringLike": { "s3:prefix": ["csv/", "csv/*"] }
      }
    }
  ]
}
```

Pas de `s3:DeleteObject` : le pipeline ne supprime rien dans S3 (la rétention `LOCAL_RETENTION_DAYS` ne
concerne que les copies locales). Les fichiers hors de `csv/` ne sont pas accessibles.

## Créer ou renouveler la clé

À faire avec un profil administrateur. La clé est écrite dans un fichier lisible par vous seul : elle ne
s'affiche ni dans le terminal ni dans l'historique du shell, et ne doit jamais être collée dans un chat.

```bash
umask 077
aws iam create-access-key --user-name kayak \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text > kayak.key
```

Reporter l'identifiant et le secret dans `.env` (sans guillemets), puis détruire le fichier
(`shred -u kayak.key`). **Ne pas conserver le fichier CSV de clés téléchargé depuis la console IAM dans le
projet** (par exemple `docs/kayak_accessKeys.csv`) : il contient le secret en clair. Pour renouveler :
créer la nouvelle clé, mettre à jour `.env`, vérifier, puis supprimer l'ancienne
(`aws iam delete-access-key`).

## Vérifier la clé (sans modifier de données)

```bash
set -a; source .env; set +a                                   # nécessite des valeurs sans espace ni guillemets
aws sts get-caller-identity --query Arn --output text         # doit afficher le user kayak
aws s3 ls s3://cdsd-kayak-datalake/csv/                       # doit réussir
aws s3 ls s3://cdsd-kayak-datalake/                           # doit être refusé (AccessDenied)
aws s3 cp /etc/hostname s3://cdsd-kayak-datalake/csv/_test.txt   # doit réussir
aws s3 rm s3://cdsd-kayak-datalake/csv/_test.txt              # doit être refusé : supprimer avec un profil admin
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN   # avant de repasser en admin
```

Sans clé, le simulateur IAM évalue la policy sans rien écrire :

```bash
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::<ID_COMPTE>:user/kayak \
  --action-names s3:PutObject s3:GetObject s3:DeleteObject \
  --resource-arns arn:aws:s3:::cdsd-kayak-datalake/csv/x.csv
```

## Une erreur 403 / AccessDenied

Lire le message : il nomme l'**action** et la **ressource** refusées. Si l'accès est légitime, ajouter cette
action sur cette ressource à la policy, au plus juste. Ne pas remplacer la clé par une clé plus puissante.

- `ListObjectsV2` refusé : le listing exige `s3:ListBucket` sur le **bucket** (pas sur `bucket/*`), avec la
  condition `s3:prefix` sur `csv/`.
- `InvalidAccessKeyId` / `InvalidClientTokenId` (et non `AccessDenied`) : la clé n'existe plus. Vérifier le
  `.env` ou la variable passée à Docker (`--env-file`), puis relancer le conteneur.
- `ParamValidationError` / `InvalidRegionError` : valeur entourée de guillemets dans `.env` (Docker
  `--env-file` les garde littéralement).

## Règles

- Une clé par projet, jamais de clé partagée.
- Pas d'`AdministratorAccess` ni de `*FullAccess`, pas de `s3:*`, pas de ressource `*`.
- Aucun secret dans le code, un notebook ou une sortie de cellule. `.env` reste hors git et en `600`.
- Activer le *secret scanning* et la *push protection* GitHub sur le dépôt.
