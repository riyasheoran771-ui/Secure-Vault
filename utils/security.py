from user_agents import parse

def get_device_info(user_agent_string):
    """Parse user agent and return device info"""
    if not user_agent_string:
        return {
            'device_type': 'unknown',
            'device_name': 'Unknown Device',
            'browser': 'Unknown Browser',
            'os': 'Unknown OS'
        }
    
    user_agent = parse(user_agent_string)
    
    if user_agent.is_mobile:
        device_type = 'mobile'
    elif user_agent.is_tablet:
        device_type = 'tablet'
    else:
        device_type = 'desktop'
    
    device_name = f"{user_agent.device.brand or 'Unknown'} {user_agent.device.model or 'Device'}".strip()
    if device_name == 'Unknown Device':
        device_name = device_type.title()
    
    return {
        'device_type': device_type,
        'device_name': device_name,
        'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}".strip(),
        'os': f"{user_agent.os.family} {user_agent.os.version_string}".strip()
    }

def check_device_restriction(user_agent_string, restriction):
    """Check if device meets the restriction criteria"""
    device_info = get_device_info(user_agent_string)
    device_type = device_info['device_type']
    
    if restriction == 'both':
        return True
    elif restriction == 'mobile':
        return device_type in ['mobile', 'tablet']
    elif restriction == 'desktop':
        return device_type == 'desktop'
    
    return True

def format_file_size(size_bytes):
    """Format file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def is_allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_extension(filename):
    """Get file extension"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''