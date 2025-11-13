import os
from flask import Flask, abort, request, jsonify
import requests
import imaplib
import logging
import ai_client
from dotenv import load_dotenv

load_dotenv(".env")


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
classifier = ai_client.client()


API_KEY = os.environ.get("API_KEY")  
if API_KEY:
    API_KEY = API_KEY.replace(" ", "")


@app.before_request
def require_api_key():
    """
    Middleware that requires X-API-Key header on every request.
    Skips check if API_KEY is unset (e.g., local dev mode).
    """
    if not API_KEY:
        # Local mode: warn once and skip check
        if not hasattr(require_api_key, "_warned"):
            logger.warning("⚠️  API_KEY not set – running in UNPROTECTED mode.")
            require_api_key._warned = True
        return  # allow everything in dev
    header_key = request.headers.get("X-API-Key")
    if header_key != API_KEY:
        abort(401)
        
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200




logger = logging.getLogger(__name__)

def log_response(resp, context=""):
    """
    Safely logs the content of a response object.
    
    Args:
        resp: The response object (e.g., requests.Response)
        context: Optional string to add context about where this response came from
    """
    try:
        if resp is None:
            logger.warning(f"{context} Response is None.")
            return

        # Attempt to parse JSON
        try:
            data = resp.json()
            if not data:
                logger.warning(f"{context} Response JSON was empty, but got a response: {resp.text}")
            else:
                logger.info(f"{context} Got response JSON: {data}")
        except ValueError as ve:
            # JSON decoding failed
            logger.warning(f"{context} Could not parse JSON: {ve}. Raw response text: {getattr(resp, 'text', '<no text>')}")
        except Exception as e:
            # Some other error accessing .json()
            logger.exception(f"{context} Unexpected error parsing JSON: {e}")

        # Optionally, log status code if available
        status_code = getattr(resp, "status_code", None)
        if status_code is not None:
            logger.info(f"{context} Response status code: {status_code}")

    except Exception as e:
        # Catch anything unexpected to make this completely bulletproof
        logger.exception(f"{context} Unexpected error while logging response: {e}")



@app.route("/pipe_mail", methods=["POST"])
def receive_mail():
    classes = ["important", "ad", "college", "other"]
    txt_max_length = 1000
    try:
        data = request.get_json()
        logger.info(f"data received: {data}")
        # Validate required fields
        required_fields = ['host', 'username', 'password', 'email_uid', "text", "html_text", "subject", "classes"]
        if not data["classes"]:
            required_fields.remove("classes")
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise Exception(f"there is no trace of the required fields {missing_fields} in the request")
        
        logger.info("about to enter in all the variables")
        host = data["host"]
        username = data["username"]
        password = data["password"]
        mail_uid = data["email_uid"]
        text = data["text"][:txt_max_length]
        html_text = data["html_text"][:txt_max_length]
        subject = data["subject"]
        if 1 > 100: #data["class_description"]
            class_description = data["class_description"]
        else:
            class_description = None
        if data["classes"]:
            classes = data["classes"]
            
        logger.info("got together all the variables")
        
        prompt = f"""
                    notes: you only see the first {txt_max_length} characters of the mail txt plain and html
                    
                    description of the classes(if None try to match the categories closely
                    and only put in those into a different category than other where you are certain): {class_description}
                    
                    subject of the mail: {subject}
                    
                    text of the mail: {text}
                     
                    html text of the mail: {html_text}
                    """
        logger.info("about to classifiy the mail")
        classified = classifier.classify_groq(text=prompt, classes=classes)
        logger.info(f"classified the mail as: {classified}")
        
        json_input = {
            "host": host,
            "port": 993,
            "username": username,
            "password": password,
            "email_uid": mail_uid,
            "source_folder": "INBOX",
            "target_folder": classified
        }
        
        # FIX: Add API key header when making internal request
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        resp = requests.post(
            url="http://localhost:3030/move-email", 
            json=json_input,
            headers=headers
        )
        
        log_response(resp=resp, context="move email function/endpoint got fetched")
        
        if resp.status_code in [200]:
            logger.info(f"succesfully moved mail {mail_uid} from inbox to {classified}")
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False}), 501
        
    except Exception as e:
        logger.error(f"Error in receive_mail: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500    
    


@app.route('/move-email', methods=['POST'])
def move_email():
    """
    Move an email to a specified folder via IMAP
    
    Expected JSON payload:
    {
        "host": "imap.mail.me.com",
        "port": 993,
        "username": "your@email.com",
        "password": "your-app-specific-password",
        "email_uid": "12345",
        "source_folder": "INBOX",
        "target_folder": "Important"
    }
    """
    mail = None
    try:
        data = request.get_json()
        logger.info(f"data received: {data}")
        # Validate required fields
        required_fields = ['host', 'username', 'password', 'email_uid']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.info(f"""about to return this: {{
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
                }}""")
            
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Extract parameters
        host = data['host']
        port = data.get('port', 993)
        username = data['username']
        password = data['password']
        email_uid = str(data['email_uid'])
        source_folder = data.get('source_folder', 'INBOX')
        target_folder = data['target_folder']
        
        logger.info(f"Attempting to move email UID {email_uid} from {source_folder} to {target_folder}")
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(host, port)
        
        # Try login with both password formats
        try:
            mail.login(username, password)
            logger.info("Login successful")
        except imaplib.IMAP4.error as e:
            password_nodash = password.replace('-', '')
            if password_nodash != password:
                mail = imaplib.IMAP4_SSL(host, port)
                mail.login(username, password_nodash)
                logger.info("Login successful with no-dash password")
            else:
                raise e
        
        # Select source folder - use INBOX in uppercase for inbox
        if source_folder.lower() == 'inbox':
            source_folder = 'INBOX'
        
        select_result = mail.select(f'"{source_folder}"')
        logger.info(f"Selected folder {source_folder}: {select_result}")
        
        # Verify the email exists
        typ, data_search = mail.uid('SEARCH', 'ALL', f'UID {email_uid}')
        if typ != 'OK' or not data_search[0]:
            mail.logout()
            
            logger.info(f"""about to return this: {{
                "success": False,
                "error": f"Email UID {email_uid} not found in {source_folder}"
                }}""")
            return jsonify({
                "success": False,
                "error": f"Email UID {email_uid} not found in {source_folder}"
            }), 404
        
        logger.info(f"Found email UID {email_uid}")
        
        # Try to create the target folder first (in case it doesn't exist)
        try:
            create_result = mail.create(f'"{target_folder}"')
            logger.info(f"Created folder {target_folder}: {create_result}")
        except Exception:
            logger.info(f"Folder {target_folder} already exists or cannot be created (this is normal)")
        
        # Copy email to target folder
        copy_result = mail.uid('COPY', email_uid, f'"{target_folder}"')
        logger.info(f"Copy result: {copy_result}")
        
        if copy_result[0] == 'OK':
            # DON'T delete the original - just copy it
            # store_result = mail.uid('STORE', email_uid, '+FLAGS', '(\\Deleted)')
            # logger.info(f"Marked for deletion: {store_result}")
            
            # expunge_result = mail.expunge()
            # logger.info(f"Expunged: {expunge_result}")
            
            logger.info(f"Successfully COPIED email UID {email_uid} from {source_folder} to {target_folder} (original kept)")
            
            mail.logout()
            
            logger.info(f"""about to return this: {{
                    "success": True,
                    "message": f"Email COPIED from {source_folder} to {target_folder} (original kept in inbox)",
                    "email_uid": email_uid,
                    "source_folder": {source_folder},
                    "target_folder": {target_folder}
                }}""")
            return jsonify({
                "success": True,
                "message": f"Email COPIED from {source_folder} to {target_folder} (original kept in inbox)",
                "email_uid": email_uid,
                "source_folder": source_folder,
                "target_folder": target_folder
            }), 200
        else:
            logger.error(f"Failed to copy email: {copy_result}")
            mail.logout()
            
            logger.info(f"""about to return this: {{
                "success": False,
                "error": f"Failed to copy email: {copy_result[1] if len(copy_result) > 1 else copy_result}"
                }}""")
            return jsonify({
                "success": False,
                "error": f"Failed to copy email: {copy_result[1] if len(copy_result) > 1 else copy_result}"
            }), 500
            
    except imaplib.IMAP4.error as e:
        # --- THIS IS THE MODIFIED LINE ---
        logger.error(f"IMAP error: {str(e)}", exc_info=True)
        # --- END OF MODIFICATION ---
        if mail:
            try:
                mail.logout()
            except Exception:
                pass
        logger.info(f"""about to return this: {{
            "success": False,
            "error": f"IMAP error: {str(e)}"
            }}""")
        return jsonify({
            "success": False,
            "error": f"IMAP error: {str(e)}"
        }), 500
        
    except Exception as e:
        # This block already had exc_info=True, so it's correct
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        if mail:
            try:
                mail.logout()
            except Exception:
                pass
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500
        
        

@app.route('/list-folders', methods=['POST'])
def list_folders():
    """
    List all available folders in the mailbox
    
    Expected JSON payload:
    {
        "host": "imap.mail.me.com",
        "port": 993,
        "username": "your@email.com",
        "password": "your-app-specific-password"
    }
    """
    mail = None
    try:
        data = request.get_json()
        
        required_fields = ['host', 'username', 'password']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        host = data['host']
        port = data.get('port', 993)
        username = data['username']
        password = data['password']
        
        logger.info(f"Connecting to {host}:{port} as {username}")
        
        mail = imaplib.IMAP4_SSL(host, port)
        
        try:
            mail.login(username, password)
            logger.info("Login successful")
        except imaplib.IMAP4.error as e:
            password_nodash = password.replace('-', '')
            if password_nodash != password:
                mail = imaplib.IMAP4_SSL(host, port)
                mail.login(username, password_nodash)
                logger.info("Login successful with no-dash password")
            else:
                raise e
        
        status, folders = mail.list()
        
        if status == 'OK':
            folder_list = []
            raw_folders = []
            for folder in folders:
                if folder:
                    # folder is a bytes object, decode it
                    decoded = folder.decode() if isinstance(folder, bytes) else str(folder)
                    raw_folders.append(decoded)
                    parts = decoded.split('"')
                    if len(parts) >= 3:
                        folder_list.append(parts[-2])
            
            mail.logout()
            
            return jsonify({
                "success": True,
                "folders": folder_list,
                "raw_folders": raw_folders
            }), 200
        else:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass
            return jsonify({
                "success": False,
                "error": "Failed to list folders"
            }), 500
            
    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}", exc_info=True)
        if mail:
            try:
                mail.logout()
            except Exception:
                pass
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3030, debug=False)