import os

DB_URI = os.getenv("DB_URI", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATE_FORMAT = "%d-%m-%Y %H:%M"
POPUP_WIDTH = 400
MAX_PINS = 100

## QUERY:
PLACES_VISITED_BY_PEOPLE_IN_PARTICULAR_DAY = """
match (person:Person)--(visit:Visit)--(place:Place)
where (date(visit.starttime) <= date( $date ) <= date(visit.endtime))
return
{
    confirmedtime: toString(person.confirmedtime),
    name: person.name,
    healthstatus: person.healthstatus,
    id: id(person)
} as person,
place,
{
    start: toString(visit.starttime),
    end: toString(visit.endtime)
} as time;
"""

PLACES_VISITED_BY_SICK_PEOPLE_IN_PARTICULAR_DAY = """
match (person:Person {healthstatus: "Sick"})--(visit:Visit)--(place:Place)
where (date(visit.starttime) <= date( $date ) <= date(visit.endtime)) and
visit.starttime.epochMillis < person.confirmedtime.epochMillis < visit.endtime.epochMillis
return
{
    confirmedtime: toString(person.confirmedtime),
    name: person.name,
    healthstatus: person.healthstatus,
    id: id(person)
} as person,
place,
{
    start: toString(visit.starttime),
    end: toString(visit.endtime)
} as time;
"""

REGISTEDED_PLACES = """
match (p:Place) return distinct collect({ name: p.name,location: p.location,type: p.type, id: id(p)}) as places
"""

PEOPLE_POSSIBLY_INFECTED_BY_PARTICULAR_PERSON = """
match (sickPerson:Person {healthstatus: "Sick"})-[sickVisit:VISITS]->(infectionPlace:Place)<-[healthyVisit:VISITS]-(healthyPerson:Person {healthstatus:"Healthy"})
where id(sickPerson) = $id and (date(sickVisit.starttime) <= date($date) <= date(sickVisit.endtime))
with
healthyPerson, infectionPlace, sickVisit, sickPerson, healthyVisit,
apoc.coll.max([sickVisit.starttime.epochMillis, healthyVisit.starttime.epochMillis]) as maxStart,
apoc.coll.min([sickVisit.endtime.epochMillis, healthyVisit.endtime.epochMillis]) as minEnd
where maxStart <= minEnd
with
healthyPerson, infectionPlace, minEnd, maxStart,
duration({ milliseconds: sum(minEnd-maxStart)}) as overlapTime
order by overlapTime desc
return
    collect({
        personName: healthyPerson.name,
        placeName: infectionPlace.name,
        placeType: infectionPlace.type,
        infectionTimeWindow: apoc.text.format('%02d:%02d:%02d', [overlapTime.hours, overlapTime.minutesOfHour, overlapTime.secondsOfMinute]),
        since: toString(datetime({epochMillis: maxStart})),
        till: toString(datetime({epochMillis: minEnd})),
        personConfirmedTime: toString(healthyPerson.confirmedtime)
    }) as dangerousMeetings
"""

#
NAMES_OF_SICK_PEOPLE = """match (person:Person {healthstatus: "Sick"}) return distinct collect(person.name) as  people;"""
VISITS_DATES = """match (v:Visit) with distinct toString(date.truncate('day',v.endtime)) as visits return collect(visits) as visits"""

PLACES_MOST_OFTEN_VISITED_BY_SICK = """
match (p:Person {healthstatus:"Sick"})-[v:VISITS]->(place:Place)
with distinct place, count(v) as sickVisits, apoc.node.degree.in(place,'VISITS') as totalVisits
order by sickVisits desc
limit 10
return  place, sickVisits, totalVisits, round(toFloat(sickVisits)/toFloat(totalVisits)*10000)/100 as percentageofsickvisits;
"""

ADD_NEW_PLACE = """
    CREATE (p:Place {name: $place_name, location: point({x:$x, y:$y}), type: $place_type})
"""

ADD_NEW_PERSON = """
    CREATE (p:Person {name: $name, healthstatus: $healthstatus, confirmedtime: datetime($confirmedtime)})
    return id(p) as person_id
"""

ADD_NEW_VISIT = """
    match (p:Person) where id(p) = $person_id
    with p
    match (pl:Place) where id(pl) = $place_id
    with p, pl
    create (p)-[:PERFORMS_VISIT]->(v:Visit { starttime:datetime($starttime), endtime:datetime($endtime)})-[:LOCATED_AT]->(pl)
    create (p)-[vi:VISITS {starttime:datetime($starttime), endtime:datetime($endtime)}]->(pl)
    set v.duration=duration.inSeconds(v.starttime,v.endtime)
    set vi.duration=duration.inSeconds(vi.starttime,vi.endtime);
"""