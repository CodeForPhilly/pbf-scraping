# create a dictionary of statute info and offense type 
# key: (title, chapter)
import pickle

offense = {}
### Unknown statute
offense[(0,0)] = 'unknown statute'

### title 18

# Inchoate crimes
offense[(18,9)] = 'inchoate crimes'
# against government
offense[(18,21)] = 'offenses against the flag'
# danger to person
offense[(18,25)] = 'criminal homicide'
offense[(18,26)] = 'crimes against unborn child'
offense[(18,27)] = 'assault'
offense[(18,28)] = 'antihazing'
offense[(18,29)] = 'kidnapping'
offense[(18,30)] = 'human trafficking'
offense[(18,31)] = 'sexual offenses'
offense[(18,32)] = 'abortion'
# offenses against property
offense[(18,33)] = 'arson, criminal mischief, and other property destruction'
offense[(18,35)] = 'burglary and other criminal intrusion'
offense[(18,37)] = 'robbery'
offense[(18,39)] = 'theft and related offenses'
offense[(18,41)] = 'forgery and fraudulent practices'
# offenses against family
offense[(18,43)] = 'offenses against the family'
# offenses against public administration
offense[(18,47)] = 'bribery and corrupt influence'
offense[(18,49)] = 'falsification and intimidation'
offense[(18,51)] = 'obstructing governmental operations'
offense[(18,53)] = 'abuse of office'
# offenses against public order and decency
offense[(18,55)] = 'riot, disorderly conduct and related offenses'
offense[(18,57)] = 'wiretapping and electronic surveillance'
offense[(18,59)] = 'public indecency'
# miscellaneous offenses
offense[(18,61)] = 'firearms and other dangerous articles'
offense[(18,63)] = 'minors'
offense[(18,65)] = 'nuisances'
offense[(18,67)] = 'proprietary and official rights'
offense[(18,69)] = 'public utilities'
offense[(18,71)] = 'sports and amusemenets'
offense[(18,73)] = 'trade and commerce'
offense[(18,75)] = 'other offenses'
offense[(18,76)] = 'computer offenses'
offense[(18,77)] = 'vehicle chop shop and illegally obtained and altered property'

### title 23
offense[(23,61)] = 'domestic relations and abuse'

### title 35
offense[(35,780)] = 'drug and substance'

### title 42 Judiciary 7 judicial procedure
offense[(42,91)] = 'arrest prior to requisition'

### title 75: traffic laws
offense[(75,1)] = 'general traffic offenses'
offense[(75,2)] = 'serious traffic offenses'
offense[(75,3)] = 'accidents report'
offense[(75,38)] = 'driving after imbibing alcohol or utilizing drugs'
offense[(75,43)] = 'vehicles: lighting equipment'
offense[(75,45)] = 'vehicles: other required equipment'


# save
with open('offense_category.pickle', 'wb') as handle:
    pickle.dump(offense, handle, protocol=pickle.HIGHEST_PROTOCOL)

# for loading
#with open('offense_category.pickle', 'rb') as handle:
#    b = pickle.load(handle)