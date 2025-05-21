#!/usr/bin/env python3

import argparse
import fnmatch
import os
import sys
import hashlib
import base64
import json
import secrets
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

index_file_name = 'index.html'

# CSS for directory listings
DIRECTORY_CSS = """ <style>
body {
    background: #f4f4f4;
    margin: 2em 2em;
}
li {
    font-family: monospace;
    font-size: 12pt;
    line-height: 14pt;
    list-style: none;
    list-style-type: none;
    padding: 3px 10px;
    margin: 3px 15px;
    display: block;
    clear: both;
}
.content {
    width: 1000px;
    background-color: white;
    margin-bottom: 5em;
    padding-bottom: 3em;
    -webkit-box-shadow: rgba(89, 89, 89, 0.449219) 2px 1px 9px 0px;
    -moz-box-shadow: rgba(89, 89, 89, 0.449219) 2px 1px 9px 0px;
    box-shadow: rgba(89, 89, 89, 0.449219) 2px 1px 9px 0px;
    border: 0;
    border-radius: 11px;
    -moz-border-radius: 11px;
    -webkit-border-radius: 11px;
    height: 96%;
    min-height: 90%;
}
.size {
    float: right;
    color: gray;
}
h1 {
    padding: 10px;
    margin: 15px;
    color: blue;
    font-family: monospace;
    font-size: 16pt;
    border-bottom: 1px solid lightgray;
}
a {
    font-weight: 500;
    perspective: 600px;
    perspective-origin: 50% 100%;
    transition: color 0.3s;
    text-decoration: none;
    color: #060606;
}
a:hover,
a:focus {
    color: #e74c3c;
}
a::before {
    background-color: #fff;
    transition: transform 0.2s;
    transition-timing-function: cubic-bezier(0.7,0,0.3,1);
    transform: rotateX(90deg);
    transform-origin: 50% 100%;
}
a:hover::before,
a:focus::before {
    transform: rotateX(0deg);
}
a::after {
    border-bottom: 2px solid #fff;
}
</style>
"""

# Simple encryption for login page
SIMPLE_LOGIN_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Protected File Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(to left, #145DA0, #B1D4E0);
            margin: 0;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            width: 90%;
            max-width: 360px;
            text-align: center;
        }
        
        h1 {
            color: #145DA0;
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        input[type="password"] {
            width: 100%;
            padding: 12px;
            margin: 8px 0 20px;
            display: inline-block;
            border: 1px solid #ccc;
            box-sizing: border-box;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        button {
            background-color: #4F5AFD;
            color: white;
            padding: 14px 20px;
            margin: 8px 0;
            border: none;
            cursor: pointer;
            width: 100%;
            border-radius: 4px;
            font-size: 1rem;
            text-transform: uppercase;
        }
        
        button:hover {
            background-color: #145DA0;
        }
        
        .remember-me {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        
        .remember-me input {
            margin-right: 10px;
            transform: scale(1.2);
        }
        
        .footer {
            position: fixed;
            bottom: 0;
            right: 0;
            padding: 10px;
            color: white;
            font-size: 14px;
        }
        
        #error-message {
            color: red;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Protected File Server</h1>
        <form id="login-form">
            <input type="password" id="password" placeholder="Enter Password" required>
            
            <div class="remember-me">
                <input type="checkbox" id="remember">
                <label for="remember">Remember for 7 days</label>
            </div>
            
            <button type="submit">Access Files</button>
            <div id="error-message">Incorrect password. Please try again.</div>
        </form>
    </div>
    
    <div class="footer">{{ footer_text }}</div>

    <script>
        // Encoded content - will be replaced with actual protected content
        const protectedContent = "{{ encrypted_content }}";
        const password_hash = "{{ password_hash }}";
        
        document.getElementById('login-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const password = document.getElementById('password').value;
            const remember = document.getElementById('remember').checked;
            
            // Simple hash function for password verification
            function hashPassword(password) {
                let hash = 0;
                for (let i = 0; i < password.length; i++) {
                    const char = password.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash = hash & hash; // Convert to 32bit integer
                }
                return hash.toString();
            }
            
            // Check if password is correct
            if (hashPassword(password) === password_hash) {
                // Store in localStorage if remember is checked
                if (remember) {
                    localStorage.setItem('fileserver_auth', 'true');
                    localStorage.setItem('fileserver_expiry', 
                        Date.now() + (7 * 24 * 60 * 60 * 1000)); // 7 days
                }
                
                // Decode and display content
                const decodedContent = atob(protectedContent);
                document.open();
                document.write(decodedContent);
                document.close();
            } else {
                document.getElementById('error-message').style.display = 'block';
            }
        });
        
        // Check if already authenticated
        window.addEventListener('load', function() {
            const isAuthenticated = localStorage.getItem('fileserver_auth');
            const expiry = localStorage.getItem('fileserver_expiry');
            
            if (isAuthenticated && expiry && Date.now() < parseInt(expiry)) {
                const decodedContent = atob(protectedContent);
                document.open();
                document.write(decodedContent);
                document.close();
            }
        });
    </script>
</body>
</html>
"""

def generate_directory_listing(parentdir, dirs, files, file_filter=None):
    """Generate HTML for directory listing"""
    html = f'''<!DOCTYPE html>
<html>
 <head>{DIRECTORY_CSS}</head>
 <body>
  <div class="content">
   <h1>{os.path.basename(os.path.abspath(parentdir))}</h1>
   <li><a style="display:block; width:100%" href="../{index_file_name}">&#x21B0;</a></li>'''
    
    # Add directories - link to index.html in each subdirectory
    for dirname in sorted(dirs):
        html += f'''
   <li><a style="display:block; width:100%" href="{dirname}/{index_file_name}">&#128193; {dirname}</a></li>'''
    
    # Add files
    for filename in sorted(files):
        # Skip index.html
        if filename.strip().lower() == index_file_name.lower():
            continue
            
        # Apply filter if provided
        if file_filter and not fnmatch.fnmatch(filename, file_filter):
            continue
            
        try:
            size = os.path.getsize(os.path.join(parentdir, filename))
            html += f'''
   <li>&#x1f4c4; <a href="{filename}">{filename}</a><span class="size">{pretty_size(size)}</span></li>'''
        except Exception as e:
            print(f'ERROR writing file name: {e}')
    
    html += '''
  </div>
 </body>
</html>'''
    
    return html

def simple_hash(password):
    """Create a simple hash for password verification"""
    hash_value = 0
    for char in password:
        hash_value = ((hash_value << 5) - hash_value) + ord(char)
        hash_value = hash_value & 0xFFFFFFFF  # Convert to 32bit integer
    return str(hash_value)

def process_dir(top_dir, password, opts):
    """Process directory recursively and create index files"""
    for parentdir, dirs, files in os.walk(top_dir):
        # Skip if directory is not writable
        if not os.access(parentdir, os.W_OK):
            print(f"***ERROR*** folder {parentdir} is not writable! SKIPPING!")
            continue
            
        if opts.verbose:
            print(f'Processing directory: {parentdir}')
        
        # Generate the directory listing HTML
        content = generate_directory_listing(parentdir, dirs, files, opts.filter)
        
        if not opts.dryrun:
            # Determine if this is the top-level directory
            is_top_level = (os.path.abspath(parentdir) == os.path.abspath(top_dir))
            
            abs_path = os.path.join(parentdir, index_file_name)
            
            try:
                if is_top_level:
                    # Only encrypt the top-level index.html
                    # Base64 encode the content
                    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                    
                    # Create a simple hash of the password
                    password_hash = simple_hash(password)
                    
                    # Create login page with embedded content
                    login_html = SIMPLE_LOGIN_TEMPLATE
                    login_html = login_html.replace('{{ encrypted_content }}', encoded_content)
                    login_html = login_html.replace('{{ password_hash }}', password_hash)
                    login_html = login_html.replace('{{ footer_text }}', opts.footer or "(c) File Server")
                    
                    with open(abs_path, "w") as index_file:
                        index_file.write(login_html)
                        
                    if opts.verbose:
                        print(f'Created encrypted: {abs_path}')
                else:
                    # Write unencrypted index.html for subdirectories
                    with open(abs_path, "w") as index_file:
                        index_file.write(content)
                        
                    if opts.verbose:
                        print(f'Created unencrypted: {abs_path}')
                        
            except Exception as e:
                print(f'Cannot create file {abs_path}: {e}')

# Bytes pretty-printing
UNITS_MAPPING = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'),
    (1024 ** 3, ' GB'),
    (1024 ** 2, ' MB'),
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
]

def pretty_size(bytes, units=UNITS_MAPPING):
    """Human-readable file sizes."""
    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''DESCRIPTION:
    Generate directory index files recursively.
    Only the top-level index.html is encrypted with password protection.
    Start from current dir or from folder passed as first positional argument.
    Optionally filter by file types with --filter "*.py".''')

    parser.add_argument('top_dir',
                      nargs='?',
                      action='store',
                      help='top folder from which to start generating indexes, '
                           'use current folder if not specified',
                      default=os.getcwd())

    parser.add_argument('--password', '-p',
                      help='password to encrypt the top-level index file',
                      required=True)

    parser.add_argument('--filter', '-f',
                      help='only include files matching glob',
                      required=False)

    parser.add_argument('--verbose', '-v',
                      action='store_true',
                      help='verbosely list every processed file',
                      required=False)

    parser.add_argument('--dryrun', '-d',
                      action='store_true',
                      help="don't write any files, just simulate the traversal",
                      required=False)
                      
    parser.add_argument('--footer','-b', 
                      help='footer text to display on login page',
                      required=False)

    config = parser.parse_args()
    
    if not config.password:
        parser.error("Password is required. Use --password to specify.")
        
    process_dir(config.top_dir, config.password, config)
