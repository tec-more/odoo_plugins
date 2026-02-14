# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ScrumSprintStage(models.Model):
    _name = 'scrum.sprint_stage'
    _description = 'Scrum Sprint Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', export_string_translation=False)

