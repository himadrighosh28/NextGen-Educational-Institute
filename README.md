# NextGen Educational Institute

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set the Flask secret key and run the application.

   **Windows PowerShell:**

   ```powershell
   $env:FLASK_SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
   python app.py
   ```

4. Open http://127.0.0.1:5000 in your browser.