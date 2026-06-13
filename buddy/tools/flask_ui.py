import json
from typing import Any, Dict, List, Optional, Union
import tempfile
import os

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger


class FlaskUITools(Toolkit):
    def __init__(self, **kwargs):
        """Initialize Flask UI Tools."""
        
        tools: List[Any] = [
            self.create_flask_app,
            self.add_route,
            self.create_html_template,
            self.create_form,
            self.run_flask_app,
            self.create_api_endpoint,
        ]

        super().__init__(name="flask_ui", tools=tools, **kwargs)

    def create_flask_app(self, app_name: str, template_folder: str = "templates", static_folder: str = "static") -> str:
        """Create a basic Flask application.

        Args:
            app_name (str): Name of the Flask application
            template_folder (str): Templates folder name
            static_folder (str): Static files folder name

        Returns:
            str: Flask app code or error message
        """
        try:
            flask_app_code = f'''from flask import Flask, render_template, request, jsonify, redirect, url_for
import os

app = Flask(__name__, 
           template_folder='{template_folder}',
           static_folder='{static_folder}')

# Secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

@app.route('/')
def index():
    \"\"\"Home page route.\"\"\"
    return render_template('index.html', title='{app_name}')

@app.errorhandler(404)
def page_not_found(e):
    \"\"\"404 error handler.\"\"\"
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    \"\"\"500 error handler.\"\"\"
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''

            return json.dumps({
                "success": "Flask app created successfully",
                "app_name": app_name,
                "code": flask_app_code,
                "filename": f"{app_name.lower().replace(' ', '_')}_app.py"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to create Flask app: {str(e)}"})

    def add_route(self, route_path: str, methods: List[str], function_name: str, template_name: Optional[str] = None, form_data: bool = False) -> str:
        """Generate Flask route code.

        Args:
            route_path (str): URL path for the route
            methods (List[str]): HTTP methods (GET, POST, etc.)
            function_name (str): Name of the route function
            template_name (Optional[str]): Template file to render
            form_data (bool): Whether route handles form data

        Returns:
            str: Flask route code or error message
        """
        try:
            methods_str = f"[{''.join([f'\"{m}\", ' for m in methods]).rstrip(', ')}]"
            
            route_code = f'''
@app.route('{route_path}', methods={methods_str})
def {function_name}():
    \"\"\"Route handler for {route_path}.\"\"\"
'''

            if form_data:
                route_code += '''    if request.method == 'POST':
        # Handle form submission
        form_data = request.form.to_dict()
        # Process form data here
        return redirect(url_for('index'))
    
'''

            if template_name:
                route_code += f'''    return render_template('{template_name}')'''
            else:
                route_code += '''    return jsonify({"message": "Route working", "path": request.path})'''

            return json.dumps({
                "success": "Route code generated successfully",
                "route_path": route_path,
                "function_name": function_name,
                "code": route_code
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to generate route: {str(e)}"})

    def create_html_template(self, template_name: str, title: str, content: str, include_bootstrap: bool = True) -> str:
        """Create an HTML template for Flask.

        Args:
            template_name (str): Name of the template file
            title (str): Page title
            content (str): HTML content
            include_bootstrap (bool): Whether to include Bootstrap CSS

        Returns:
            str: HTML template code or error message
        """
        try:
            bootstrap_cdn = '''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>''' if include_bootstrap else ''

            html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ title or '{title}' }}}}</title>{bootstrap_cdn}
    <link rel="stylesheet" href="{{{{ url_for('static', filename='style.css') }}}}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{{{ url_for('index') }}}}">{title}</a>
        </div>
    </nav>

    <div class="container mt-4">
        {{% block content %}}
        {content}
        {{% endblock %}}
    </div>

    <script src="{{{{ url_for('static', filename='script.js') }}}}"></script>
</body>
</html>'''

            return json.dumps({
                "success": "HTML template created successfully",
                "template_name": template_name,
                "code": html_template,
                "filename": template_name if template_name.endswith('.html') else f"{template_name}.html"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to create template: {str(e)}"})

    def create_form(self, form_name: str, fields: List[Dict], submit_text: str = "Submit", method: str = "POST") -> str:
        """Create an HTML form.

        Args:
            form_name (str): Name/ID of the form
            fields (List[Dict]): List of form fields with type, name, label, required
            submit_text (str): Text for submit button
            method (str): Form method (POST/GET)

        Returns:
            str: HTML form code or error message
        """
        try:
            form_html = f'<form id="{form_name}" method="{method}" class="needs-validation" novalidate>\n'
            
            for field in fields:
                field_type = field.get('type', 'text')
                field_name = field.get('name', '')
                field_label = field.get('label', field_name.title())
                field_required = field.get('required', False)
                field_placeholder = field.get('placeholder', '')
                field_options = field.get('options', [])

                form_html += '    <div class="mb-3">\n'
                form_html += f'        <label for="{field_name}" class="form-label">{field_label}</label>\n'

                if field_type == 'select':
                    form_html += f'        <select class="form-select" id="{field_name}" name="{field_name}"{"" if not field_required else " required"}>\n'
                    form_html += f'            <option value="">Choose...</option>\n'
                    for option in field_options:
                        option_value = option if isinstance(option, str) else option.get('value', '')
                        option_text = option if isinstance(option, str) else option.get('text', option_value)
                        form_html += f'            <option value="{option_value}">{option_text}</option>\n'
                    form_html += '        </select>\n'
                elif field_type == 'textarea':
                    form_html += f'        <textarea class="form-control" id="{field_name}" name="{field_name}" rows="3" placeholder="{field_placeholder}"{"" if not field_required else " required"}></textarea>\n'
                else:
                    form_html += f'        <input type="{field_type}" class="form-control" id="{field_name}" name="{field_name}" placeholder="{field_placeholder}"{"" if not field_required else " required"}>\n'

                if field_required:
                    form_html += '        <div class="invalid-feedback">Please provide a valid value.</div>\n'
                
                form_html += '    </div>\n'

            form_html += f'    <button type="submit" class="btn btn-primary">{submit_text}</button>\n'
            form_html += '</form>\n'

            # Add JavaScript for form validation
            validation_script = '''
<script>
// Bootstrap form validation
(function() {
    'use strict';
    window.addEventListener('load', function() {
        var forms = document.getElementsByClassName('needs-validation');
        var validation = Array.prototype.filter.call(forms, function(form) {
            form.addEventListener('submit', function(event) {
                if (form.checkValidity() === false) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }, false);
})();
</script>'''

            return json.dumps({
                "success": "Form created successfully",
                "form_name": form_name,
                "html": form_html,
                "validation_script": validation_script,
                "full_code": form_html + validation_script
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to create form: {str(e)}"})

    def create_api_endpoint(self, endpoint_path: str, method: str, response_data: Dict, requires_auth: bool = False) -> str:
        """Create a REST API endpoint.

        Args:
            endpoint_path (str): API endpoint path
            method (str): HTTP method
            response_data (Dict): Sample response data structure
            requires_auth (bool): Whether endpoint requires authentication

        Returns:
            str: API endpoint code or error message
        """
        try:
            function_name = endpoint_path.replace('/', '_').replace('-', '_').strip('_')
            if not function_name:
                function_name = "api_endpoint"

            auth_decorator = '''
@app.before_request
def require_auth():
    if request.endpoint and 'api' in request.endpoint:
        # Add your authentication logic here
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
''' if requires_auth else ''

            endpoint_code = f'''{auth_decorator}
@app.route('/api{endpoint_path}', methods=['{method}'])
def api_{function_name}():
    \"\"\"API endpoint for {endpoint_path}.\"\"\"
    try:'''

            if method == 'GET':
                endpoint_code += f'''
        # Handle GET request
        response_data = {json.dumps(response_data, indent=8)}
        return jsonify(response_data), 200'''
            elif method == 'POST':
                endpoint_code += f'''
        # Handle POST request
        data = request.get_json()
        if not data:
            return jsonify({{"error": "No JSON data provided"}}), 400
        
        # Process the data here
        response_data = {json.dumps(response_data, indent=8)}
        return jsonify(response_data), 201'''
            elif method == 'PUT':
                endpoint_code += f'''
        # Handle PUT request
        data = request.get_json()
        if not data:
            return jsonify({{"error": "No JSON data provided"}}), 400
        
        # Update logic here
        response_data = {json.dumps(response_data, indent=8)}
        return jsonify(response_data), 200'''
            elif method == 'DELETE':
                endpoint_code += f'''
        # Handle DELETE request
        # Delete logic here
        return jsonify({{"message": "Resource deleted successfully"}}), 200'''

            endpoint_code += '''
    except Exception as e:
        return jsonify({"error": str(e)}), 500'''

            return json.dumps({
                "success": "API endpoint created successfully",
                "endpoint_path": f"/api{endpoint_path}",
                "method": method,
                "function_name": f"api_{function_name}",
                "code": endpoint_code
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to create API endpoint: {str(e)}"})

    def run_flask_app(self, app_file: str, host: str = "0.0.0.0", port: int = 5000, debug: bool = True) -> str:
        """Generate code to run Flask application.

        Args:
            app_file (str): Python file containing Flask app
            host (str): Host to bind to
            port (int): Port to run on
            debug (bool): Whether to run in debug mode

        Returns:
            str: Run command and instructions or error message
        """
        try:
            run_code = f'''
# To run your Flask application:
# 1. Save your Flask code to {app_file}
# 2. Install Flask: pip install flask
# 3. Run the application:

import os
from {app_file.replace('.py', '')} import app

if __name__ == '__main__':
    # Set environment variables
    os.environ['FLASK_APP'] = '{app_file}'
    os.environ['FLASK_ENV'] = '{"development" if debug else "production"}'
    
    # Run the application
    app.run(host='{host}', port={port}, debug={debug})

# Or run directly from command line:
# flask run --host={host} --port={port}'''

            requirements = '''flask>=2.0.0
werkzeug>=2.0.0'''

            return json.dumps({
                "success": "Flask run configuration created",
                "run_code": run_code,
                "requirements": requirements,
                "host": host,
                "port": port,
                "debug": debug,
                "url": f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to create run configuration: {str(e)}"})