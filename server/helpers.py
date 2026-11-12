from flask import request

def paginate(query):
    """Turns any Model.query into a paginated JSON response.
    Use ?page=1&per_page=10 in the URL."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)