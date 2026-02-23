# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Odoo 17 post_init_hook receives a ready-made `env`."""
    Section = env['mysdb.section'].sudo()
    Project = env['mysdb.project'].sudo()
    Relation = env['mysdb.product_relation'].sudo()
    Product = env['mysdb.product'].sudo()

    # Map legacy project.section_id -> section.project_id (only when unambiguous)
    section_to_projects = {}
    for proj in Project.search([('section_id', '!=', False)]):
        section_to_projects.setdefault(proj.section_id.id, []).append(proj)

    for section_id, projects in section_to_projects.items():
        section = Section.browse(section_id)
        if not section.exists():
            continue
        if len(projects) == 1:
            if not section.project_id:
                section.project_id = projects[0].id
        else:
            if not section.project_id:
                _logger.warning(
                    "Section %s is linked to multiple projects; leaving project_id empty.",
                    section.display_name,
                )

    # Backfill product_relation.section_id from legacy project.section_id
    for rel in Relation.search([('section_id', '=', False), ('project_id', '!=', False)]):
        legacy_section = rel.project_id.section_id
        if legacy_section:
            rel.section_id = legacy_section.id

    # Backfill product.section_id from product_relation.section_id
    for product in Product.search([('section_id', '=', False)]):
        rel = Relation.search([('product_id', '=', product.id), ('section_id', '!=', False)], limit=1)
        if rel:
            product.section_id = rel.section_id.id

