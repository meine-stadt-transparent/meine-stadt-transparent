# TODO

"""
# In[]

from django.core.management import call_command
from django.utils import timezone

from importer.models import ExternalList
from importer.tests.utils import MockLoader, old_date, make_system, make_body, make_list, make_file, make_paper

system = make_system()
body = make_body()

# In[]
# 1. Load a fixture with two papers and two users, with one user beeing subscribed to one paper, and the external lists loaded

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

new_date = timezone.now().astimezone().replace(microsecond=0)

file1 = make_file(1)
file2 = make_file(2)
file2["modified"] = new_date
file1["modified"] = new_date
paper1 = make_paper([file1], paper_id=1)
paper1["modified"] = new_date
paper2 = make_paper([file2], paper_id=2)
paper2["modified"] = new_date

loader.api_data[body["paper"]] = make_list([paper1, paper2])

# In[]

# 5. Run cron. Check that exactely the one user got one notification for the one paper

call_command('cron')

# In[]

# 6. Run cron. Check that nothing happend

call_command('cron')

"""
