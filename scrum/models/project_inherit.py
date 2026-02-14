# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectProjectInherit(models.Model):
    _inherit = 'project.project'

    team_ids = fields.One2many('scrum.team', 'project_id', string='Scrum Teams')
