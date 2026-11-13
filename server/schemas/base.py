from marshmallow import EXCLUDE, Schema, pre_load


class BaseSchema(Schema):
    """Every schema in the project extends this one."""

    class Meta:
        unknown = EXCLUDE  # ignore extra fields the frontend sends (e.g. id)

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Trims spaces so '  ' counts as empty. Passwords are left untouched."""
        if not hasattr(data, "items"):
            return data
        return {
            key: value.strip() if isinstance(value, str) and key != "password" else value
            for key, value in data.items()
        }