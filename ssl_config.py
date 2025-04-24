import os
import ssl
import certifi
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def configure_ssl():
    """Configure SSL settings for the entire application"""
    try:
        # Get certifi's CA bundle path
        ca_bundle = certifi.where()
        
        # Verify the CA bundle exists
        if not Path(ca_bundle).exists():
            raise FileNotFoundError(f"CA bundle not found at: {ca_bundle}")
        
        # Debug output
        logging.debug(f"Using CA Bundle: {ca_bundle}")
        logging.debug(f"CA Bundle exists: {Path(ca_bundle).exists()}")
        
        # Create a custom SSL context
        ssl_context = ssl.create_default_context(cafile=ca_bundle)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Patch the default SSL context
        ssl._create_default_https_context = lambda: ssl_context
        
        # For AWS SDK specifically
        os.environ['AWS_CA_BUNDLE'] = ca_bundle
        os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle
        
        return True
    except FileNotFoundError as fnf_err:
        logging.error(f"FileNotFoundError: {fnf_err}")
        return False
    except Exception as e:
        logging.error(f"SSL configuration failed: {str(e)}", exc_info=True)
        return False

# Configure SSL when this module is imported
ssl_configured = configure_ssl()
if not ssl_configured:
    logging.warning("Warning: SSL configuration failed. Falling back to system defaults.")