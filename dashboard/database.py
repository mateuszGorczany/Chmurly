from typing import Callable, Any
from neo4j import GraphDatabase, basic_auth
from neo4j.work.simple import Session

def with_session(function: Callable):
    def do_in_session(self, *args, **kwargs):
        with self.driver.session() as session:
            return function(self, session, *args, **kwargs)
    return do_in_session

class Database:

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))

    def close(self):
        self.driver.close()


    @with_session
    def write(self, session: Session, function: Callable, *args, **kwargs) -> Any:
        return session.write_transaction(function, *args, **kwargs)

    @with_session
    def read(self, session: Session, function: Callable) -> Any:
        return session.read_transaction(function)