{
    'name': 'Hotel Manager',
    'version': '18.0.1.0.0',
    'summary': 'Rooms, bookings, billing and reports for small hotels',
    'category': 'Services',
    'author': 'Olajide',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/room_type_views.xml',
        'views/room_views.xml',
        'views/menu.xml',
    ],
    'application': True,
    'installable': True,
}
