# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from . import models
from . import wizard
from . import controllers
try:
  import html2text
except:
  raise UserError("html2text module not found. try 'sudo pip3 install html2text'")