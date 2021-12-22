import streamlit as st
import pandas as pd
import folium
import datetime
from streamlit_folium import folium_static
from utils import add_mouse_position_to_map, min_max_coordinates, parse_and_format_date, parse_time, beautify_location
from database import Database
from constants import ADD_NEW_PERSON, ADD_NEW_PLACE, ADD_NEW_VISIT, DB_URI, DB_USER, DB_PASSWORD, DATE_FORMAT, PEOPLE_POSSIBLY_INFECTED_BY_PARTICULAR_PERSON, PLACES_MOST_OFTEN_VISITED_BY_SICK, PLACES_VISITED_BY_PEOPLE_IN_PARTICULAR_DAY, PLACES_VISITED_BY_SICK_PEOPLE_IN_PARTICULAR_DAY, POPUP_WIDTH, REGISTEDED_PLACES, VISITS_DATES, MAX_PINS
from dateutil.parser import parse as parse_stringtime

"""
# Chmurly
Analiza danych covidowych w oparciu o sztucznie wygenerowany dataset z możliwością dodawania swoich rekordów.
"""

DB = Database(
    st.secrets["DB_URI"],
    st.secrets["DB_USER"],
    st.secrets["DB_PASSWORD"]
)

def date_of_all_visits():
    visits = DB.read(lambda tx: tx.run(VISITS_DATES).data()[0]["visits"])
    visits.sort(key=lambda date: datetime.datetime.strptime(date, "%Y-%m-%d"))
    option = st.selectbox("Wybierz dzień", visits)

    return option

def draw_places(interactive_map, places):
    for place in places:
        folium.Marker(
            location=place,
        ).add_to(interactive_map)
    add_mouse_position_to_map(interactive_map)

def create_map_marker(visit):
    start= parse_stringtime(visit.get("time", {}).get("start"))
    end = parse_stringtime(visit.get("time", {}).get("end"))
    place = visit.get("place", {})
    return folium.Marker(
        location=beautify_location(visit.get("place", {}).get("location")),
        popup=folium.Popup(
            html=f"""
                <b>Kto:</b> {visit.get("person", {}).get("name")} <br>
                <b>Gdzie:</b>: {place.get("name")} <br>
                <b>Typ(eng):</b> {place.get("type")} <br>
                <b>Od</b> {start.strftime(DATE_FORMAT)} <b>do</b> {end.strftime(DATE_FORMAT)} <br>
                <b>Stan zdrowia: </b>{visit["person"]["healthstatus"]}<br>
                <b>potwierdzony dnia:</b> {parse_and_format_date(visit["person"]["confirmedtime"])}<br>
            """,
            max_width=POPUP_WIDTH
        )
    )

def places(date, by_sick=True):
    visits = DB.read(
        lambda tx: tx.run(
            PLACES_VISITED_BY_SICK_PEOPLE_IN_PARTICULAR_DAY if by_sick else PLACES_VISITED_BY_PEOPLE_IN_PARTICULAR_DAY,
            date=date).data()
    )
    interactive_map = folium.Map()
    locations = []
    for visit in visits[:MAX_PINS]:
        locations.append(visit.get("place", {}).get("location"))
        create_map_marker(visit).add_to(interactive_map)

    interactive_map.fit_bounds(min_max_coordinates(locations))
    add_mouse_position_to_map(interactive_map)

    folium_static(interactive_map)
    return visits

"""
## Miejsca najczęściej odwiedzane przez zakażonych
"""


def most_dangerous_places():
    most_dangerous_places = DB.read(
        lambda tx: tx.run(PLACES_MOST_OFTEN_VISITED_BY_SICK).data()
    )
    interactive_map = folium.Map()
    locations = []
    for place in most_dangerous_places:
        locations.append(place.get("place", {}).get("location"))
        folium.Marker(
            location=place["place"]["location"],
            popup=folium.Popup(f"""
                <b>Nazwa:</b> {place["place"]["name"]} <br>
                <b>Typ(eng):</b> {place["place"]["type"]} <br>
                <b>Wizyty:</b> {place["totalVisits"]} <br>
                <b>Wizyty odbyte przez zakażonych:</b>{place["percentageofsickvisits"]}%  <br>
            """,
            max_width=POPUP_WIDTH
            )
        ).add_to(interactive_map)

    interactive_map.fit_bounds(min_max_coordinates(locations))
    add_mouse_position_to_map(interactive_map)

    folium_static(interactive_map)

most_dangerous_places()


"## Miejsca odwiedzone w danym dniu"
by_sick = st.checkbox("Przez osoby zakażone")
date = date_of_all_visits()
visits = places(date, by_sick=by_sick)

"### Osoby, które mogły zostać zakażone w tym dniu"

def sick_selector(visits_on_day):
    sick_people = [visit.get("person", {}) for visit in visits_on_day if visit["person"]["healthstatus"] == "Sick"]
    names = [person.get("name") for person in sick_people]
    selected_person_name = st.selectbox("Wybierz osobę", names)

    return visits_on_day[names.index(selected_person_name)]

selected_person_visit = sick_selector(visits)
st.write(f"""
    **Kto:** {selected_person_visit["person"]["name"]} \n
    **Gdzie:** {selected_person_visit["place"]["name"]} \n
    **Czas:** od
    { parse_and_format_date(selected_person_visit["time"]["start"])} do
    { parse_and_format_date(selected_person_visit["time"]["start"])}\n
    **Status zdrowia:** {selected_person_visit["person"]["healthstatus"]}\n
    **Data potwierdzenia statusu zdrowia**: {parse_and_format_date(selected_person_visit["person"]["confirmedtime"])}
""")

possibly_infected = DB.read(
    lambda tx: tx.run(PEOPLE_POSSIBLY_INFECTED_BY_PARTICULAR_PERSON, date=date, id=selected_person_visit.get("person", {}).get("id")).data()[0]["dangerousMeetings"]
)

if possibly_infected:
    df_possibly_infected = pd.DataFrame(possibly_infected)
    df_possibly_infected = df_possibly_infected[[
        "personName", "placeName", "placeType", "since", "till", "infectionTimeWindow", "personConfirmedTime"
    ]]
    for column in ["since", "till", "personConfirmedTime"]:
        df_possibly_infected[column] = df_possibly_infected[column].apply(parse_and_format_date)

    "Osoby narażone:"
    st.write(df_possibly_infected.rename(columns={
        "personName": "imię i nazwisko",
        "placeName": "nazwa miejsca",
        "placeType": "typ miejsca(eng)",
        "since": "kontakt od",
        "till": "kontakt do",
        "infectionTimeWindow": "czas narażenia",
        "personConfirmedTime": "data potwierdzenia COVID",
    }))
else:
    "Nikt nie był narażony na zarażenie w tym czasie."

"""
# Dodawanie nowych rekordów:
"""
"## Dostępne miejsca:"


def all_places():
    registered_places = DB.read(
        lambda tx: tx.run(REGISTEDED_PLACES).data()[0]["places"]
    )
    interactive_map = folium.Map()
    locations = []
    for place in registered_places:
        locations.append(place.get("location"))
        folium.Marker(
            location=place["location"],
            popup=folium.Popup(f"""
                <b>Nazwa:</b> {place["name"]} <br>
                <b>Typ(eng):</b> {place["type"]} <br>
                <b>ID:</b> {place["id"]} <br>
            """,
            max_width=POPUP_WIDTH
            )
        ).add_to(interactive_map)

    interactive_map.fit_bounds(min_max_coordinates(locations))
    add_mouse_position_to_map(interactive_map)

    folium_static(interactive_map)


all_places()

"""
## Wprowadź nowe miejsce
"""
def add_new_place(place_name, location, place_type):
    DB.write(lambda tx: tx.run(ADD_NEW_PLACE, x=location[0], y=location[1], place_name=place_name, place_type=place_type))

with st.form("new_place"):
    place_name = st.text_input("Nazwa")
    place_type = st.text_input("Typ")
    latitude = st.number_input("Szerokość geograficzna")
    longitude = st.number_input("Długość geograficzna")
    new_location = [latitude, longitude]

    submitted = st.form_submit_button("Dodaj miejsce")
    if submitted:
        add_new_place(place_name, new_location, place_type)

"""
## Dodaj nową osobę
"""
def add_new_person():
    with st.form("new_person"):
        name = st.text_input("Imię i nazwisko")
        new_person_health_status = st.selectbox("Stan zdrowia", ["Healthy", "Sick"])
        confirm_date = st.date_input("Data potwierdzenia statusu zdrowia")
        confirm_time = st.text_input("Czas potwierdzenia statusu zdrowia", placeholder="np. 19:45")

        submitted = st.form_submit_button("Dodaj osobę")
        if submitted:
            confirm_datetime = datetime.datetime.combine(confirm_date, parse_time(confirm_time))
            person_id = DB.write(lambda tx: tx.run(
                ADD_NEW_PERSON,
                name=name,
                healthstatus=new_person_health_status,
                confirmedtime=confirm_datetime.isoformat()
            ).data()[0]["person_id"])
            st.write(f"ID (proszę zapamiętać!): {person_id}")

add_new_person()

"""
## Dodaj nową wizytę danej osoby w danym miejscu
"""
def add_new_visit():
    with st.form("new_visit"):
        person_id = int(st.number_input("ID osoby", step=1, format="%d"))
        place_id = int(st.number_input("ID miejsca", step=1, format="%d"))
        start_date = st.date_input("Data odwiedzin")
        start_time = st.text_input("Czas odwiedzin", placeholder="np. 19:45")
        end_date = st.date_input("Data końca odwiedzin")
        end_time =st.text_input("Czas końca odwiedzin", placeholder="np. 19:45")

        submitted = st.form_submit_button("Dodaj wizytę")
        if submitted:
            start_datetime = datetime.datetime.combine(start_date, parse_time(start_time))
            end_datetime = datetime.datetime.combine(end_date, parse_time(end_time))
            DB.write(lambda tx: tx.run(
                ADD_NEW_VISIT,
                starttime=start_datetime.isoformat(),
                endtime=end_datetime.isoformat(),
                person_id=person_id,
                place_id=place_id
            ))

add_new_visit()