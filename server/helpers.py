from flask import request

def paginate(query):
    #Turns any Model.query into a paginated JSON response.
    #Use ?page=1&per_page=10 in the URL.
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": schema.dump(result.items, many=True),
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }


def get_data():
    #Reads JSON body safely (returns {} instead of crashing).
    return request.get_json(silent=True) or {}