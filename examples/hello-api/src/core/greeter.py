"""Core greeting logic - no web framework dependencies."""


def greet(name: str, formal: bool = False) -> str:
    """Generate a greeting for the given name.
    
    Args:
        name: The name to greet
        formal: If True, use formal greeting
        
    Returns:
        A greeting string
    """
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")
    
    name = name.strip()
    
    if formal:
        return f"Good day, {name}. How may I assist you?"
    return f"Hello, {name}!"
