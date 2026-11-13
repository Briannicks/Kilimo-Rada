from .auth import bp as auth
from .broadcasts import bp as broadcasts
from .farmers import bp as farmers
from .prices import bp as prices
from .registry import bp as registry
from .reports import bp as reports
from .users import bp as users
from .ussd import bp as ussd


def register_routes(app):
    for bp in (auth, users, farmers, reports, prices, broadcasts, ussd, registry):
        app.register_blueprint(bp, url_prefix="/api")