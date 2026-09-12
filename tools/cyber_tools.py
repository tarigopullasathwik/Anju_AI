import socket
import re

def port_scanner(host: str, ports: list = [21, 22, 23, 25, 53, 80, 110, 443, 3306, 3389]):
    """
    Very basic port scanner to identify open common ports on a given host.
    """
    open_ports = []
    try:
        # Resolve hostname if needed
        ip = socket.gethostbyname(host)
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((ip, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
    except Exception as e:
        return f"Error scanning ports: {e}"

    if open_ports:
        return f"Scan complete for {host}. Open ports found: {', '.join(map(str, open_ports))}"
    else:
        return f"Scan complete for {host}. No common open ports found."

def url_detector(url: str):
    """
    Detects if a URL looks suspicious based on common patterns.
    """
    suspicious_patterns = [
        r"\.zip$", r"\.exe$", r"\.scr$", r"\.pif$",
        r"bit\.ly", r"tinyurl\.com",
        r"login", r"verify", r"account", r"bank",
        r"@[a-z0-9]", # User info in URL
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", # IP address instead of domain
    ]

    score = 0
    for pattern in suspicious_patterns:
        if re.search(pattern, url.lower()):
            score += 1

    if score >= 2:
        return f"Warning: The URL '{url}' looks highly suspicious. Proceed with extreme caution."
    elif score == 1:
        return f"The URL '{url}' has some suspicious characteristics. Be careful."
    else:
        return f"The URL '{url}' appears to be relatively safe based on basic pattern matching."
