# -*- coding: utf-8 -*-
import base64
import json
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
    backlog_type = fields.Selection([
        ('epic', _('Epic')),
        ('feature', _('Feature')),
    ], string='Type', default='feature')
    priority = fields.Integer(string='Priority', default=1)
    level = fields.Integer(string='Level', default=1, compute='_compute_level', store=True)
    path = fields.Char(string='Path', compute='_compute_path', store=True, help='Full path with parent names separated by /')
    status = fields.Selection([
        ('to_do', _('To Do')),
        ('in_progress', _('In Progress')),
        ('done', _('Done')),
    ], string='Status', default='to_do')
    estimated_story_points = fields.Float(string='Estimated Story Points')
    user_story_ids = fields.One2many('scrum.user_story', 'product_backlog_id', string='User Stories')

    requirement_file = fields.Binary(string='Requirement File', attachment=True)
    requirement_filename = fields.Char(string='Filename')
    parse_status = fields.Selection([
        ('none', _('Not Parsed')),
        ('parsing', _('Parsing')),
        ('done', _('Parsed')),
        ('error', _('Parse Error')),
    ], string='Parse Status', default='none', tracking=True)
    parse_error = fields.Text(string='Parse Error Message')
    parsed_stories_json = fields.Json(string='Parsed User Stories JSON')
    parsed_stories_json_formatted = fields.Text(string='Formatted JSON', compute='_compute_parsed_stories_json_formatted')

    @api.depends('parsed_stories_json')
    def _compute_parsed_stories_json_formatted(self):
        for record in self:
            if record.parsed_stories_json:
                record.parsed_stories_json_formatted = json.dumps(
                    record.parsed_stories_json,
                    indent=2,
                    ensure_ascii=False
                )
            else:
                record.parsed_stories_json_formatted = False

    @api.depends('user_story_ids', 'user_story_ids.status')
    def _compute_total_story_points(self):
        for record in self:
            record.total_story_points = sum(story.estimated_story_points for story in record.user_story_ids)
    
    @api.depends('user_story_ids', 'user_story_ids.status')
    def _compute_story_progress(self):
        for record in self:
            stories = record.user_story_ids
            total_stories = len(stories)
            if total_stories == 0:
                record.completed_stories = 0
                record.total_stories = 0
                record.story_completion_percentage = 0.0
                continue
            
            completed_stories = sum(1 for story in stories if story.status == 'done')
            record.completed_stories = completed_stories
            record.total_stories = total_stories
            record.story_completion_percentage = (completed_stories / total_stories * 100) if total_stories > 0 else 0.0
    
    completed_stories = fields.Integer(string='Completed Stories', compute='_compute_story_progress', store=True)
    total_stories = fields.Integer(string='Total Stories', compute='_compute_story_progress', store=True)
    story_completion_percentage = fields.Float(string='Story Completion %', compute='_compute_story_progress', store=True, digits=(5, 2))

    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for record in self:
            if not record.parent_id:
                record.level = 1
            else:
                record.level = record.parent_id.level + 1

    @api.depends('name', 'parent_id', 'parent_id.path')
    def _compute_path(self):
        for record in self:
            if record.parent_id:
                record.path = f"{record.parent_id.path}/{record.name}" if record.parent_id.path else record.name
            else:
                record.path = record.name

    total_story_points = fields.Float(string='Total Story Points', compute='_compute_total_story_points', store=True)

    def action_parse_requirement(self):
        self.ensure_one()
        if not self.requirement_file:
            raise UserError(_('Please upload a requirement file first.'))
        
        self.parse_status = 'parsing'
        self.parse_error = False
        
        try:
            file_content = base64.b64decode(self.requirement_file)
            file_ext = self.requirement_filename.lower().split('.')[-1] if self.requirement_filename else ''
            
            if file_ext in ['txt', 'md']:
                text_content = file_content.decode('utf-8')
            elif file_ext == 'json':
                text_content = file_content.decode('utf-8')
            else:
                text_content = file_content.decode('utf-8', errors='ignore')
            # 解析内容为树结构
            tree_data = self._parse_content_to_tree(text_content, file_ext)
            
            self.parsed_stories_json = tree_data
            # 递归创建嵌套结构
            self._create_nested_structure(tree_data, self.id, self.project_id.id)
            
            self.parse_status = 'done'
            
        except Exception as e:
            self.parse_status = 'error'
            self.parse_error = str(e)
            _logger.error('Failed to parse requirement file: %s', e)
            raise UserError(_('Failed to parse requirement file: %s') % e)

    def _parse_content_to_tree(self, content, file_ext):
        if file_ext == 'json':
            try:
                data = json.loads(content)
                return self._normalize_json_structure(data)
            except json.JSONDecodeError:
                pass
        
        root = {'children': [], 'level': 0, 'is_task': False}
        stack = [root]
        priority = 10
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            header_level = 0
            title = ''
            is_task = False
            if line.startswith('#'):
                match = re.match(r'^(#{1,6})\s+(.+)', line)
                if match:
                    header_level = len(match.group(1))
                    title = match.group(2).strip()
                    if title.lower().startswith('[task]') or title.lower().startswith('[任务]'):
                        is_task = True
                        title = re.sub(r'^\[(task|任务)\]\s*', '', title, flags=re.IGNORECASE).strip()
            
            if header_level > 0:
                node = {
                    'name': title,
                    'description': '',
                    'acceptance_criteria': '',
                    'priority': priority,
                    'children': [],
                    'tasks': [],
                    'level': header_level,
                    'is_task': is_task,
                }
                priority += 10
                
                while len(stack) > 1 and stack[-1]['level'] >= header_level:
                    stack.pop()
                
                if is_task and stack[-1].get('is_task') == False and stack[-1].get('children') == []:
                    stack[-1]['tasks'].append(node)
                else:
                    stack[-1]['children'].append(node)
                    stack.append(node)
            
            elif line.startswith('- ') or line.startswith('* '):
                current = stack[-1]
                if current.get('children') is not None and len(current.get('children', [])) == 0:
                    current['acceptance_criteria'] += line.lstrip('-* ') + '\n'
                else:
                    current['description'] += line.lstrip('-* ') + '\n'
            
            elif stack[-1] != root:
                stack[-1]['description'] += line + '\n'
        
        return root.get('children', [])

    def _normalize_json_structure(self, data):
        if isinstance(data, list):
            return [self._normalize_node(node) for node in data]
        elif isinstance(data, dict):
            if data.get('type') == 'epic':
                children = data.get('children', [])
                return [self._normalize_node(node) for node in children]
            elif 'children' in data:
                return [self._normalize_node(node) for node in data.get('children', [])]
            else:
                return [self._normalize_node(data)]
        return []

    def _normalize_node(self, node):
        if not isinstance(node, dict):
            return node
        normalized = {
            'name': node.get('name', 'Untitled'),
            'type': node.get('type', ''),
            'description': node.get('description', ''),
            'priority': node.get('priority', 10),
            'acceptance_criteria': node.get('acceptance_criteria', ''),
            'estimated_story_points': node.get('estimated_story_points', 0.0),
            'tasks': node.get('tasks', []),
        }
        children = node.get('children', [])
        if children:
            normalized['children'] = [self._normalize_node(child) for child in children]
        else:
            normalized['children'] = []
        return normalized

    def _create_nested_structure(self, nodes_data, parent_backlog_id, project_id):
        for node_data in nodes_data:
            children = node_data.get('children', [])
            tasks = node_data.get('tasks', [])
            node_type = node_data.get('type', '')
            has_children = children and len(children) > 0
            has_tasks = tasks and len(tasks) > 0
            
            if node_type == 'story':
                user_story = self.env['scrum.user_story'].create({
                    'name': node_data.get('name', 'Untitled Story'),
                    'description': node_data.get('description', ''),
                    'acceptance_criteria': node_data.get('acceptance_criteria', ''),
                    'product_backlog_id': parent_backlog_id,
                    'project_id': project_id,
                    'priority': node_data.get('priority', 10),
                    'estimated_story_points': node_data.get('estimated_story_points', 0.0),
                })
            elif node_type in ('epic', 'feature'):
                child_backlog = self.env['scrum.product_backlog'].create({
                    'name': node_data.get('name', 'Untitled'),
                    'description': node_data.get('description', ''),
                    'project_id': project_id,
                    'parent_id': parent_backlog_id,
                    'priority': node_data.get('priority', 10),
                    'backlog_type': node_type if node_type in ('epic', 'feature') else 'feature',
                })
                self._create_nested_structure(children, child_backlog.id, project_id)
            else:
                user_story = self.env['scrum.user_story'].create({
                    'name': node_data.get('name', 'Untitled Story'),
                    'description': node_data.get('description', ''),
                    'acceptance_criteria': node_data.get('acceptance_criteria', ''),
                    'product_backlog_id': parent_backlog_id,
                    'project_id': project_id,
                    'priority': node_data.get('priority', 10),
                    'estimated_story_points': node_data.get('estimated_story_points', 0.0),
                })

    def action_view_parsed_stories(self):
        self.ensure_one()
        return {
            'name': _('Parsed User Stories'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.user_story',
            'view_mode': 'list,form',
            'domain': [('product_backlog_id', '=', self.id)],
            'context': {'default_product_backlog_id': self.id, 'default_project_id': self.project_id.id},
        }
