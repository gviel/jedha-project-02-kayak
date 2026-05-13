# Spécifications script : rds_postgresql_full.py

## Role
provisioning de la base de données RDS

# Déroulement 
  - provisioning VPC
  - provisioning instance RDS PostgreSQL (one-time)
  - suppression de l'instance une fois la démo terminée.
  - Type d'instance configurable avec par défaut: db.t4g.micro (équivalent « très petit»), stockage gp3 20 GB, pas de snapshots/backups
