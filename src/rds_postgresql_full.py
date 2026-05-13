import boto3
import time
import logging
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
load_dotenv()


#username = os.environ["PG_USERNAME"]
#password= os.environ["PG_PWD"]
#rds_endpoint= os.environ["PG_HOST"]

# -----------------------
# CONFIGURATION
# -----------------------
REGION = "eu-west-3"  # Paris
DB_IDENTIFIER = "demo-postgres-instance"
DB_NAME = "demo_db"
MASTER_USERNAME = "admin"
MASTER_PASSWORD = "MotDePasseSecurise123!"
DB_INSTANCE_CLASS = "db.t3.micro"
ALLOCATED_STORAGE = 20  # Go

# -----------------------
# LOGGING
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------
# CREATION DES CLIENTS AWS
# -----------------------
ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)


# -----------------------
# CREER UN VPC PERSONNALISÉ
# -----------------------
def create_vpc():
    try:
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
        ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": "demo-vpc"}])
        logger.info(f"VPC créé : {vpc_id}")
        return vpc_id
    except ClientError as e:
        logger.error(f"Erreur création VPC : {e}")
        raise


# -----------------------
# CREER UN SUBNET ET UN SG
# -----------------------
def setup_network(vpc_id):
    try:
        subnet = ec2.create_subnet(
            VpcId=vpc_id, CidrBlock="10.0.1.0/24", AvailabilityZone=f"{REGION}a"
        )
        subnet_id = subnet["Subnet"]["SubnetId"]
        ec2.create_tags(Resources=[subnet_id], Tags=[{"Key": "Name", "Value": "demo-subnet"}])

        sg = ec2.create_security_group(
            GroupName="demo-sg",
            Description="Groupe de sécurité pour RDS PostgreSQL",
            VpcId=vpc_id
        )
        sg_id = sg["GroupId"]

        # Autorise les connexions PostgreSQL depuis n'importe où (à restreindre en prod)
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 5432,
                    "ToPort": 5432,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                }
            ]
        )

        logger.info(f"Subnet créé : {subnet_id}, SG : {sg_id}")
        return subnet_id, sg_id
    except ClientError as e:
        logger.error(f"Erreur configuration réseau : {e}")
        raise


# -----------------------
# CREER LE RDS POSTGRESQL
# -----------------------
def create_rds_instance(subnet_id, sg_id):
    try:
        subnet_group_name = "demo-subnet-group"
        rds.create_db_subnet_group(
            DBSubnetGroupName=subnet_group_name,
            DBSubnetGroupDescription="Demo subnet group",
            SubnetIds=[subnet_id]
        )
        logger.info("Groupe de sous-réseaux RDS créé")

        rds.create_db_instance(
            DBInstanceIdentifier=DB_IDENTIFIER,
            AllocatedStorage=ALLOCATED_STORAGE,
            DBInstanceClass=DB_INSTANCE_CLASS,
            Engine="postgres",
            MasterUsername=MASTER_USERNAME,
            MasterUserPassword=MASTER_PASSWORD,
            DBName=DB_NAME,
            Port=5432,
            PubliclyAccessible=True,
            VpcSecurityGroupIds=[sg_id],
            DBSubnetGroupName=subnet_group_name,
            DeletionProtection=False,
            MultiAZ=False,
            Tags=[{"Key": "Name", "Value": "DemoRDS"}]
        )
        logger.info("Instance RDS en cours de création…")
    except ClientError as e:
        logger.error(f"Erreur création RDS : {e}")
        raise


# -----------------------
# ATTENTE DISPONIBILITÉ RDS
# -----------------------
def wait_for_rds_available():
    while True:
        try:
            response = rds.describe_db_instances(DBInstanceIdentifier=DB_IDENTIFIER)
            status = response["DBInstances"][0]["DBInstanceStatus"]
            logger.info(f"Statut actuel : {status}")
            if status == "available":
                logger.info("Instance RDS prête !")
                break
            time.sleep(30)
        except ClientError as e:
            logger.error(f"Erreur lors de l’attente : {e}")
            break


# -----------------------
# SUPPRIMER RDS
# -----------------------
def delete_rds_instance():
    try:
        rds.delete_db_instance(
            DBInstanceIdentifier=DB_IDENTIFIER,
            SkipFinalSnapshot=True
        )
        logger.info("Suppression de l’instance RDS en cours…")
    except ClientError as e:
        if "DBInstanceNotFound" in str(e):
            logger.warning("Instance déjà supprimée.")
        else:
            logger.error(f"Erreur suppression RDS : {e}")
            raise

    # Attente de suppression complète
    while True:
        try:
            rds.describe_db_instances(DBInstanceIdentifier=DB_IDENTIFIER)
            logger.info("Toujours en cours de suppression RDS…")
            time.sleep(30)
        except rds.exceptions.DBInstanceNotFoundFault:
            logger.info("Instance RDS supprimée.")
            break


# -----------------------
# SUPPRIMER LE VPC ET RESSOURCES
# -----------------------
def delete_vpc(vpc_id, subnet_id, sg_id):
    try:
        logger.info("Nettoyage des ressources réseau…")

        ec2.delete_security_group(GroupId=sg_id)
        ec2.delete_subnet(SubnetId=subnet_id)
        ec2.delete_vpc(VpcId=vpc_id)

        logger.info(f"VPC {vpc_id} et ressources associées supprimés.")
    except ClientError as e:
        logger.error(f"Erreur suppression VPC : {e}")


# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    try:
        vpc_id = create_vpc()
        subnet_id, sg_id = setup_network(vpc_id)

        create_rds_instance(subnet_id, sg_id)
        wait_for_rds_available()

        logger.info("Exécution terminée. (Instance prête, suppression dans 1 min)")
        time.sleep(60)

        delete_rds_instance()
        delete_vpc(vpc_id, subnet_id, sg_id)

        logger.info("Nettoyage complet terminé ✅")

    except Exception as e:
        logger.error(f"Erreur fatale : {e}")
