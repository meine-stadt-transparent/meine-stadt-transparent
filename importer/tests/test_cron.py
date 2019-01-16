# TODO

"""
# In[]

from django.core.management import call_command

from importer.models import ExternalList
from importer.tests.utils import MockLoader, old_date, make_system, make_body, make_list, make_file, make_paper

system = make_system()
body = make_body()

# In[]
# 1. Load a fixture with two papers and two users, with one user beeing subscribed to one file, and the external lists loaded

ExternalList(url=system["body"], last_update=old_date).save()
ExternalList(url=body["person"], last_update=old_date).save()
ExternalList(url=body["meeting"], last_update=old_date).save()
ExternalList(url=body["organization"], last_update=old_date).save()
ExternalList(url=body["paper"], last_update=old_date).save()

# In[]

# 2. Mock the importer (does minio need to be mocked?) and the email service

loader = MockLoader(system)
loader.api_data[system["id"]] = system
loader.api_data[system["body"]] = make_list([body])
loader.api_data[body["id"]] = body
loader.api_data[body["meeting"]] = make_list([])
loader.api_data[body["organization"]] = make_list([])
loader.api_data[body["paper"]] = make_list([])

# We have no changed data import yet
loader.api_data[body["paper"]] = make_list([])

# In[]

# 3. Run cron. Check that nothing happend

call_command('cron')

# In[]

# 4. Mock an extern list with changes to both paper

files1 = [make_file(0), make_file(1)]
files2 = [make_file(2), make_file(3)]

loader.api_data[body["paper"]] = make_list([make_paper(files1, paper_id=0), make_paper(files2, paper_id=1)])

# In[]

# 5. Run cron. Check that exactely the one user got one notification for the one paper

call_command('cron')

# In[]

# 6. Run cron. Check that nothing happend

call_command('cron')

"""
