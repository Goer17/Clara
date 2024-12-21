import json, re
from typing import (
    List, Tuple, Dict,
    Literal
)

import neo4j

class Graph:
    def __init__(
            self,
            uri: str,
            auth: Tuple[str, str]
        ):
        self.__driver = neo4j.GraphDatabase.driver(
            uri=uri,
            auth=auth
        )
    
    @staticmethod
    def json_dumps(data: Dict[str, str | int | float]) -> str:
        json_str = json.dumps(data)
        json_str = re.sub(r'"\s*([^"]+)\s*"\s*:', r'\1:', json_str)

        return json_str
    
    def close(self):
        self.__driver.close()
    
    def create_node(
            self,
            labels: List[str],
            properties: Dict[str, str | int | float],
        ) -> 'Node':
        _labels = ":".join(labels)
        _properties = Graph.json_dumps(properties)
        query = (
            f"CREATE (p:{_labels} {_properties})\n"
            f"RETUEN id(p) AS id"
        )
        try:
            with self.__driver.session() as session:
                result = session.run(
                    query=query
                )
                id = result.single()["id"]
                node = Node._create(graph=self, id=id, labels=labels, properties=properties)
                return node
        except Exception as e:
            pass
        return None

    def match_node(
            self,
            id: int | None = None,
            labels: List[str] = [],
            properties: Dict = {},
            order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
            limit: int | None = None
        ) -> List['Node']:
        if id is not None:
            query = (
                f"MATCH (p)\n"
                f"WHERE id(p) = {id}\n",
                f"RETURN p\n"
            )
        else:
            _labels = ":" + ":".join(labels) if len(labels) > 0 else ""
            _properties = Graph.json_dumps(properties) if len(properties) > 0 else ""
            query = (
                f"MATCH (p{_labels} {_properties})\n"
                f"RETURN p\n"
            )
            if order is not None:
                _k, _m = order
                query += f"ORDER BY p.{_k} {_m}\n"
            if limit is not None:
                query += f"LIMIT {limit}"
        try:
            with self.__driver.session() as session:
                nodes = []
                results = session.run(
                    query=query
                )
                for record in results:
                    p = record["p"]
                    p_id = p.id
                    p_labels = list(p.labels)
                    p_props = dict(p)
                    node = Node._create(graph=self, id=p_id, labels=p_labels, properties=p_props)
                    nodes.append(node)
                return nodes      
        except Exception as e:
            print(e)
        return []
    
    def update_node(
            self,
            id: str,
            new_labels: List[str] = [],
            new_properties: Dict = {}
        ) -> bool:
        query = (
            f"MATCH (p) WHERE id(p) = {id}"
            
        )
    

class Node:
    def __init__(self):
        self.__graph = None
        self.id = None
        self.labels = None
        self.properties = None
        self.alive = False
        raise RuntimeError("Use Graph.create_node or Graph.match_node to get a Node instance")

    @classmethod
    def _create(cls, graph: Graph, id: int, labels: List[str], properties: Dict[str, str | int | float]) -> 'Node':
        instance = cls.__new__(cls)
        instance.__graph = graph
        instance.id = id
        instance.labels = labels
        instance.properties = properties
        instance.alive = True

        return instance


class Relationship:
    pass