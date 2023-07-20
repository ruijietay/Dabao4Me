import boto3
import configparser

####################################### Parameters #######################################

# Create config parser and read config file
config = configparser.ConfigParser()
config.read("config.ini")

# Load bot token
bot_token = config["bot_keys"]["current_bot_token"]

########## Initialising DB and Required Tables ##########

# The name of our table in DynamoDB
tableName = "Dabao4Me_Requests"

# Create resource object to access DynamoDB
db = boto3.resource('dynamodb', 
                    region_name = config["dynamodb"]["region_name"], 
                    aws_access_key_id = config["dynamodb"]["aws_access_key_id"],
                    aws_secret_access_key = config["dynamodb"]["aws_secret_access_key"])


# Create table object with specified table name
table = db.Table(tableName)

# The table tracking user ratings
userRatingsTable = db.Table("Dabao4Me_User_Ratings")