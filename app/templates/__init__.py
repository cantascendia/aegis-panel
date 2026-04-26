from datetime import datetime
from typing import Union

import jinja2

from app.config.env import CUSTOM_TEMPLATES_DIRECTORY
from app.utils._aegis_clocks import now_utc_naive
from .filters import CUSTOM_FILTERS

template_directories = ["app/templates"]
if CUSTOM_TEMPLATES_DIRECTORY:
    # User's templates have priority over default templates
    template_directories.insert(0, CUSTOM_TEMPLATES_DIRECTORY)

env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_directories))
env.filters.update(CUSTOM_FILTERS)
env.globals["now"] = now_utc_naive


def render_template(template: str, context: Union[dict, None] = None) -> str:
    return env.get_template(template).render(context or {})
