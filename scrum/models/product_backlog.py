# -*- coding: utf-8 -*-
from odoo import models, fields, api,_

class ScrumProductBacklog(models.Model):
    _name = 'scrum.product_backlog'
    _description = 'Scrum Product Backlog'
    _order = 'priority desc, create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('scrum.product_backlog', string='Parent Product Backlog', index=True, domain="['!', ('id', 'child_of', id)]", tracking=True)
    child_ids = fields.One2many('scrum.product_backlog', 'parent_id', string="Sub Product Backlog", export_string_translation=False)
    priority = fields.Integer(string='Priority', default=1)
    level = fields.Integer(string='Level', default=1, compute='_compute_level', store=True)
    status = fields.Selection([
        ('to_do', _('To Do')),
        ('in_progress', _('In Progress')),
        ('done', _('Done')),
    ], string='Status', default='to_do')
    estimated_story_points = fields.Float(string='Estimated Story Points')
    user_story_ids = fields.One2many('scrum.user_story', 'product_backlog_id', string='User Stories')
    # sprint_backlog_ids = fields.One2many('scrum.sprint_backlog', 'product_backlog_id', string='Sprint Backlogs')

    @api.depends('user_story_ids')
    def _compute_total_story_points(self):
        for record in self:
            record.total_story_points = sum(story.estimated_story_points for story in record.user_story_ids)

    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for record in self:
            if not record.parent_id:
                record.level = 1
            else:
                record.level = record.parent_id.level + 1


    total_story_points = fields.Float(string='Total Story Points', compute='_compute_total_story_points', store=True)
