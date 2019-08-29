from setuptools import setup

setup(
    name='IESEG_inter_matcher',
    version='1.0',
    py_modules=['munkresJu', "sendMails"],
    install_requires=[
        'Click',
        'sklearn',
        'munkres',
        'pandas',
        'unidecode',
    ],
    entry_points='''
        [console_scripts]
        match=munkresJu:match
        send_mails=sendMails:send_mails
    ''',
)
