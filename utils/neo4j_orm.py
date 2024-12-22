import json, re
from typing import (
    List, Tuple, Dict,
    Literal
)
import neo4j
from shortuuid import uuid

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
            labels: List[str] = ["memory"],
            properties: Dict[str, str | int | float] = {},
        ) -> 'Node':
        if "memory" not in labels:
            labels.append("memory")
        _labels = ":".join(labels)
        if "m_id" not in properties:
            properties["m_id"] = uuid()
        _properties = Graph.json_dumps(properties)
        query = (
            f"CREATE (p:{_labels} {_properties})\n"
        )
        try:
            with self.__driver.session() as session:
                session.run(
                    query=query
                )
                node = Node._create(graph=self, m_id=properties["m_id"], labels=labels, properties=properties)
                return node
        except Exception as e:
            pass
        return None

    def match_node(
            self,
            m_id: str | None = None,
            labels: List[str] = ["memory"],
            properties: Dict = {},
            order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
            limit: int | None = None
        ) -> List['Node']:
        if "memory" not in labels:
            labels.append("memory")
        if m_id is not None:
            query = (
                f"MATCH (p:memory {{ m_id: '{m_id}' }})\n"
                f"RETURN p\n"
            )
        else:
            _labels = ":".join(labels)
            _properties = Graph.json_dumps(properties) if len(properties) > 0 else ""
            query = (
                f"MATCH (p:{_labels} {_properties})\n"
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
                    m_id = p["m_id"]
                    p_labels = list(p.labels)
                    p_props = dict(p)
                    node = Node._create(graph=self, m_id=m_id, labels=p_labels, properties=p_props)
                    nodes.append(node)
                return nodes      
        except Exception as e:
            print(e)
        return []
    
    def _update_node(
            self,
            m_id: str,
            new_labels: List[str] = [],
            new_properties: Dict = {},
            removed_properties: List[str] = []
        ) -> bool:
        query = (
            f"MATCH (p {{ m_id: '{m_id}' }})\n"
            f"FOREACH (label IN labels(p) | REMOVE p:$(label))\n"
            f"FOREACH (label IN $new_labels | SET p:$(label))\n"
            f"FOREACH (key IN keys($new_properties) | SET p[key] = $new_properties[key])\n"
            f"FOREACH (rkey IN $removed_properties | REMOVE p[rkey])\n"
        )
        parameters = {
            "new_labels": new_labels,
            "new_properties" : new_properties,
            "removed_properties": removed_properties
        }
        try:
            with self.__driver.session() as session:
                session.run(
                    query=query,
                    parameters=parameters
                )
            return True
        except Exception as e:
            pass
        
        return False

    def _delete_node(
            self,
            m_id: str
        ) -> bool:
        query = (
            f"MATCH (p:memory {{ m_id: '{m_id}' }})\n"
            f"DETACH DELETE p\n"
        )
        try:
            with self.__driver.session() as session:
                session.run(
                    query=query
                )
            return True
        except Exception as e:
            pass
        return False

class Node:
    def __init__(self):
        self.__graph: Graph = None
        self.m_id = None
        self.labels = None
        self._properties = None
        self._alive = False
        self._new_properties = {}
        self._removed_properties = []
        raise RuntimeError("Use Graph.create_node or Graph.match_node to get a Node instance")

    @classmethod
    def _create(cls, graph: Graph, m_id: int, labels: List[str], properties: Dict[str, str | int | float]) -> 'Node':
        instance = cls.__new__(cls)
        instance.__graph = graph
        instance.m_id = m_id
        instance.labels = labels
        instance._properties = properties
        instance._alive = True
        instance._new_properties = {}
        instance._removed_properties = []
        
        return instance

    @staticmethod
    def ensure_node_alive(method):
        def wrapper(self, *args, **kwargs):
            if not getattr(self, '_alive', True):
                raise RuntimeError("This node was already removed from graph")
            return method(self, *args, **kwargs)
        return wrapper
    
    @ensure_node_alive
    def __str__(self):
        label = ""
        for lb in self.labels:
            if lb != "memory":
                label = lb
                break
        return f"[{label}] {self._properties}"
    
    @ensure_node_alive
    def get_prop(self, key: str) -> str | int | float:
        return self._properties.get(key)
    
    @ensure_node_alive
    def set_prop(self, key: str, value: str | int | float):
        self._properties[key] = value
        self._new_properties[key] = value
    
    @ensure_node_alive
    def remove_prop(self, key: str):
        self._properties.pop(key)
        if key not in self._removed_properties:
            self._removed_properties.append(key)
    
    @ensure_node_alive
    def set_label(self, label: str):
        self.labels = ["memory", label]
    
    @ensure_node_alive
    def update(self) -> bool:
        if not self._alive:
            return False
        self.__graph._update_node(
            m_id=self.m_id,
            new_labels=self.labels,
            new_properties=self._new_properties,
            removed_properties=self._removed_properties
        )
        self._new_properties = {} # refresh
        return True
    
    @ensure_node_alive
    def create_rela(self, to: 'Node', label: 'str', content: 'str') -> bool:
        # TODO
        pass
    
    @ensure_node_alive
    def neighbors(self) -> List[Tuple['Node', 'Relationship']]:
        # TODO
        pass
    
    @ensure_node_alive
    def destroy(self) -> bool:
        if self.__graph._delete_node(self.m_id):
            self._alive = False
            return True
        return False

class Relationship:
    def __init__(self):
        self.__graph: Graph = None
        self.r_id = None
        self.label = None
        self._properties = None
        self._alive = False
        self._new_properties = {}
        self._removed_properties = []
        raise RuntimeError("Use Node.create_rela to get a Relationship instance")
    
    @classmethod
    def _create():
        pass
    
    
    