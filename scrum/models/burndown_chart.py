# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ScrumBurndownData(models.Model):
    _name = 'scrum.burndown_data'
    _description = 'Scrum Burndown Chart Data'
    _order = 'date asc'

    name = fields.Char(string='Name', required=True, compute='_compute_name', store=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    
    total_story_points = fields.Float(string='Total Story Points', default=0.0, help='Total story points for the sprint')
    remaining_story_points = fields.Float(string='Remaining Story Points', default=0.0, help='Story points remaining on this date')
    completed_story_points = fields.Float(string='Completed Story Points', default=0.0, help='Story points completed by this date')
    
    total_tasks = fields.Integer(string='Total Tasks', default=0, help='Total tasks for the sprint')
    remaining_tasks = fields.Integer(string='Remaining Tasks', default=0, help='Tasks remaining on this date')
    completed_tasks = fields.Integer(string='Completed Tasks', default=0, help='Tasks completed by this date')
    
    total_hours = fields.Float(string='Total Hours', default=0.0, help='Total estimated hours for the sprint')
    remaining_hours = fields.Float(string='Remaining Hours', default=0.0, help='Hours remaining on this date')
    completed_hours = fields.Float(string='Completed Hours', default=0.0, help='Hours completed by this date')
    
    ideal_remaining = fields.Float(string='Ideal Remaining', compute='_compute_ideal_remaining', store=True, help='Ideal remaining work if on track')
    variance = fields.Float(string='Variance', compute='_compute_variance', store=True, help='Difference between actual and ideal remaining')
    
    notes = fields.Text(string='Notes')

    @api.depends('sprint_plan_id', 'date')
    def _compute_name(self):
        for record in self:
            if record.sprint_plan_id and record.date:
                record.name = f"{record.sprint_plan_id.name} - {record.date}"
            else:
                record.name = 'Burndown Data'

    @api.depends('sprint_plan_id', 'date', 'total_story_points')
    def _compute_ideal_remaining(self):
        for record in self:
            if not record.sprint_plan_id or not record.date:
                record.ideal_remaining = 0.0
                continue
            
            start_date = record.sprint_plan_id.start_date
            end_date = record.sprint_plan_id.end_date
            
            if not start_date or not end_date:
                record.ideal_remaining = record.total_story_points
                continue
            
            total_days = (end_date - start_date).days + 1
            elapsed_days = (record.date - start_date).days + 1
            
            if elapsed_days <= 0:
                record.ideal_remaining = record.total_story_points
            elif elapsed_days >= total_days:
                record.ideal_remaining = 0.0
            else:
                ideal_per_day = record.total_story_points / total_days
                record.ideal_remaining = record.total_story_points - (ideal_per_day * elapsed_days)

    @api.depends('remaining_story_points', 'ideal_remaining')
    def _compute_variance(self):
        for record in self:
            record.variance = record.remaining_story_points - record.ideal_remaining

    @api.constrains('date', 'sprint_plan_id')
    def _check_date_within_sprint(self):
        for record in self:
            if record.sprint_plan_id:
                if record.sprint_plan_id.start_date and record.date < record.sprint_plan_id.start_date:
                    raise UserError(_('Date cannot be before sprint start date.'))
                if record.sprint_plan_id.end_date and record.date > record.sprint_plan_id.end_date:
                    raise UserError(_('Date cannot be after sprint end date.'))


class ScrumBurndownChart(models.Model):
    _name = 'scrum.burndown_chart'
    _description = 'Scrum Burndown Chart'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True, ondelete='cascade')
    
    chart_type = fields.Selection([
        ('story_points', _('Story Points')),
        ('tasks', _('Tasks')),
        ('hours', _('Hours')),
        ('combined', _('Combined')),
    ], string='Chart Type', default='story_points', required=True)
    
    data_ids = fields.One2many('scrum.burndown_data', 'sprint_plan_id', string='Burndown Data')
    
    current_date = fields.Date(string='Current Date', default=fields.Date.today, help='Date to show current progress')
    
    summary_text = fields.Text(string='Summary', compute='_compute_summary', store=True)
    
    @api.depends('sprint_plan_id', 'chart_type', 'data_ids', 'current_date')
    def _compute_summary(self):
        for record in self:
            if not record.data_ids:
                record.summary_text = ''
                continue
            
            data = record.data_ids.sorted('date')
            if not data:
                record.summary_text = ''
                continue
            
            total = data[0].total_story_points
            remaining = data[-1].remaining_story_points
            completed = total - remaining
            completion_percentage = (completed / total * 100) if total > 0 else 0
            
            ideal_remaining = data[-1].ideal_remaining
            variance = data[-1].variance
            
            status = 'On Track' if abs(variance) < (total * 0.1) else ('Behind' if variance > 0 else 'Ahead')
            
            summary = f"""Sprint Burndown Summary for {record.sprint_plan_id.name}:
    
Total Work: {total:.1f} story points
Completed: {completed:.1f} story points ({completion_percentage:.1f}%)
Remaining: {remaining:.1f} story points
    
Ideal Remaining: {ideal_remaining:.1f} story points
Variance: {variance:+.1f} story points
Status: {status}
    """
            record.summary_text = summary

    def action_generate_burndown_data(self):
        self.ensure_one()
        if not self.sprint_plan_id:
            raise UserError(_('Please select a Sprint Plan first.'))
        
        sprint_plan = self.sprint_plan_id
        
        existing_data = self.env['scrum.burndown_data'].search([
            ('sprint_plan_id', '=', sprint_plan.id)
        ])
        
        if existing_data:
            raise UserError(_('Burndown data already exists for this sprint. Clear it first if you want to regenerate.'))
        
        self._generate_daily_data(sprint_plan)
        self._update_daily_progress(sprint_plan)

    def _generate_daily_data(self, sprint_plan):
        self.ensure_one()
        
        start_date = sprint_plan.start_date
        end_date = sprint_plan.end_date
        
        if not start_date or not end_date:
            raise UserError(_('Sprint must have start and end dates.'))
        
        total_story_points = 0.0
        total_tasks = 0
        total_hours = 0.0
        
        for backlog in sprint_plan.sprint_backlog_ids:
            if backlog.user_story_id:
                total_story_points += backlog.user_story_id.estimated_story_points
            total_tasks += backlog.total_tasks
            total_hours += sum(task.estimated_hours for task in backlog.sprint_task_ids)
        
        current_date = start_date
        while current_date <= end_date:
            self.env['scrum.burndown_data'].create({
                'sprint_plan_id': sprint_plan.id,
                'date': current_date,
                'total_story_points': total_story_points,
                'total_tasks': total_tasks,
                'total_hours': total_hours,
                'remaining_story_points': total_story_points,
                'remaining_tasks': total_tasks,
                'remaining_hours': total_hours,
            })
            
            current_date += timedelta(days=1)

    def _update_daily_progress(self, sprint_plan):
        self.ensure_one()
        
        burndown_data = self.env['scrum.burndown_data'].search([
            ('sprint_plan_id', '=', sprint_plan.id)
        ], order='date asc')
        
        if not burndown_data:
            return
        
        done_stage = self.env['scrum.sprint_stage'].search([('name', '=ilike', 'Done')], limit=1)
        
        for data_point in burndown_data:
            completed_story_points = 0.0
            completed_tasks = 0
            completed_hours = 0.0
            
            for backlog in sprint_plan.sprint_backlog_ids:
                for task in backlog.sprint_task_ids:
                    task_done_date = None
                    
                    if task.sprint_stage_id.id == done_stage.id if done_stage else False:
                        task_done_date = self._get_task_done_date(task, data_point.date)
                    
                    if task_done_date and task_done_date <= data_point.date:
                        completed_tasks += 1
                        completed_hours += task.actual_hours if task.actual_hours else task.estimated_hours
                        
                        if backlog.user_story_id:
                            completed_story_points += backlog.user_story_id.estimated_story_points / backlog.total_tasks if backlog.total_tasks > 0 else 0
            
            data_point.write({
                'completed_tasks': completed_tasks,
                'completed_hours': completed_hours,
                'completed_story_points': completed_story_points,
                'remaining_tasks': data_point.total_tasks - completed_tasks,
                'remaining_hours': data_point.total_hours - completed_hours,
                'remaining_story_points': data_point.total_story_points - completed_story_points,
            })

    def _get_task_done_date(self, task, date_limit):
        self.ensure_one()
        
        done_stage = self.env['scrum.sprint_stage'].search([('name', '=ilike', 'Done')], limit=1)
        if not done_stage:
            return None
        
        message = self.env['mail.message'].search([
            ('res_id', '=', task.id),
            ('model', '=', 'scrum.sprint_task'),
            ('date', '<=', date_limit),
            ('message_type', 'in', ['notification']),
        ], order='date desc', limit=1)
        
        if message and message.date:
            return message.date.date()
        
        return None

    def action_refresh_burndown_data(self):
        self.ensure_one()
        if not self.sprint_plan_id:
            raise UserError(_('Please select a Sprint Plan first.'))
        
        self._update_daily_progress(self.sprint_plan_id)

    def action_clear_burndown_data(self):
        self.ensure_one()
        if not self.sprint_plan_id:
            raise UserError(_('Please select a Sprint Plan first.'))
        
        existing_data = self.env['scrum.burndown_data'].search([
            ('sprint_plan_id', '=', self.sprint_plan_id.id)
        ])
        
        if existing_data:
            existing_data.unlink()
    
    def action_view_burndown_data(self):
        self.ensure_one()
        return {
            'name': _('Burndown Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.burndown_data',
            'view_mode': 'tree,graph',
            'domain': [('sprint_plan_id', '=', self.sprint_plan_id.id)],
            'context': {
                'default_sprint_plan_id': self.sprint_plan_id.id,
                'group_by': ['date'],
            },
        }
    
    def get_burndown_chart_data(self):
        self.ensure_one()
        burndown_data = self.data_ids.sorted('date')
        
        dates = [d.date.strftime('%Y-%m-%d') for d in burndown_data]
        actual_remaining = [d.remaining_story_points for d in burndown_data]
        ideal_remaining = [d.ideal_remaining for d in burndown_data]
        
        return {
            'dates': dates,
            'actual_remaining': actual_remaining,
            'ideal_remaining': ideal_remaining,
            'total': burndown_data[0].total_story_points if burndown_data else 0,
        }