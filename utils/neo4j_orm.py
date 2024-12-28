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
            label: str | None = None,
            properties: Dict[str, str | int | float] = {},
        ) -> 'Node':
        labels = ["memory"]
        if label is not None and label != "memory":
            labels.append(label)
        _labels = ":".join(labels)
        if "m_id" not in properties:
            properties["m_id"] = uuid()
        _properties = Graph.json_dumps(properties)
        query = (
            f"CREATE (p:{_labels} {_properties})\n"
        )
        with self.__driver.session() as session:
            session.run(
                query=query
            )
        node = Node._create(graph=self, m_id=properties["m_id"], label=label, properties=properties)
        return node

    def match_node(
            self,
            m_id: str | None = None,
            label: str | None = None,
            properties: Dict = {},
            order: Tuple[str, Literal["ASC", "DESC"]] | None = None,
            limit: int | None = None
        ) -> List['Node']:
        labels = ["memory"]
        if label is not None and label != "memory":
            labels.append(label)
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
                    p_label = p_labels[1] if p_labels[1] != "memory" else p_labels[0]
                    p_props = dict(p)
                    node = Node._create(graph=self, m_id=m_id, label=p_label, properties=p_props)
                    nodes.append(node)
                return nodes      
        except Exception as e:
            print(e)
        return []
    
    def _update_node(
            self,
            m_id: str,
            new_label: str,
            new_properties: Dict = {},
            removed_properties: List[str] = []
        ):
        query = (
            f"MATCH (p {{ m_id: '{m_id}' }})\n"
            f"FOREACH (label IN labels(p) | REMOVE p:$(label))\n"
            f"FOREACH (label IN $new_labels | SET p:$(label))\n"
            f"FOREACH (key IN keys($new_properties) | SET p[key] = $new_properties[key])\n"
            f"FOREACH (rkey IN $removed_properties | REMOVE p[rkey])\n"
        )
        parameters = {
            "new_labels": ["memory", new_label],
            "new_properties" : new_properties,
            "removed_properties": removed_properties
        }
        with self.__driver.session() as session:
            session.run(
                query=query,
                parameters=parameters
            )

    def _delete_node(
            self,
            m_id: str
        ):
        query = (
            f"MATCH (p:memory {{ m_id: '{m_id}' }})\n"
            f"DETACH DELETE p\n"
        )
        with self.__driver.session() as session:
            session.run(
                query=query
            )
    
    def _create_rela(
            self,
            pos: Tuple[str, str],
            label: str,
            properties: Dict[str, str | int | float]
        ) -> 'Relationship':
        from_m_id, to_m_id = pos
        properties["from"] = from_m_id
        properties["to"] = to_m_id
        properties["r_id"] = uuid()
        query = (
            f"MATCH (p:memory {{ m_id: '{from_m_id}' }})\n"
            f"MATCH (q:memory {{ m_id: '{to_m_id}' }})\n"
            f"CREATE (p)-[r:{label}]->(q)\n"
            f"FOREACH (key IN keys($properties) | SET r[key] = $properties[key])\n"
        )
        parameters = {
            "properties": properties
        }
        with self.__driver.session() as session:
            session.run(
                query=query,
                parameters=parameters
            )
        rela = Relationship._create(
            graph=self,
            r_id=properties["r_id"],
            pos=pos,
            label=label,
            properties=properties
        )
        return rela

    def match(
            self,
            from_prop: Dict[str, str | int | float] = {},
            to_prop: Dict[str, str | int | float] = {},
            rela_prop: Dict[str, str | int | float] = {},
            bidirect: bool = False
        ) -> List[Tuple['Node', 'Relationship', 'Node']]:
        from_labels = ["memory"]
        to_labels = ["memory"]
        if "label" in from_prop:
            from_labels.append(from_prop.pop("label"))
        if "label" in to_prop:
            to_labels.append(to_prop.pop("label"))
        _from_labels = ":".join(from_labels)
        _from_prop = Graph.json_dumps(from_prop)
        _to_labels = ":".join(to_labels)
        _to_prop = Graph.json_dumps(to_prop)
        _r_label = ":" + rela_prop.pop("label") if "label" in rela_prop else ""
        _rela_prop = Graph.json_dumps(rela_prop)
        arrow = "->" if not bidirect else "-"
        query = (
            f"MATCH (p:{_from_labels} {_from_prop})\n"
            f"MATCH (q:{_to_labels} {_to_prop})\n"
            f"MATCH (p)-[r{_r_label} {_rela_prop}]{arrow}(q)\n"
            f"RETURN p, r, q\n"
        )
        with self.__driver.session() as session:
            ans = []
            result = session.run(
                query=query
            )
            for record in result:
                p, q = record['p'], record['q']
                p_labels, q_labels = p.labels, q.labels
                p_prop, q_prop = dict(p), dict(q)
                node_p = Node._create(
                    graph=self,
                    m_id=p_prop["m_id"],
                    labels=p_labels,
                    properties=p_prop
                )
                node_q = Node._create(
                    graph=self,
                    m_id=q_prop["m_id"],
                    labels=q_labels,
                    properties=q_prop
                )
                r = record['r']
                r_label = r.type
                r_prop = dict(r)
                r_id = r_prop["r_id"]
                from_m_id = r_prop["from"]
                to_m_id = r_prop["to"]
                rela = Relationship._create(
                    graph=self,
                    r_id=r_id,
                    pos=(from_m_id, to_m_id),
                    label=r_label,
                    properties=r_prop
                )
                ans.append((node_p, rela, node_q))
            return ans
    
    def update_rela(
            self,
            r_id: str,
            pos: Tuple[str, str],
            new_properties: Dict[str, str | int | float]
        ):
        from_m_id, to_m_id = pos
        query = (
            f"MATCH (p:memory {{ m_id: '{from_m_id}' }})\n"
            f"MATCH (q:memory {{ m_id: '{to_m_id}' }})\n"
            f"MATCH (p)-[r {{ r_id: '{r_id}' }}]->(q)\n"
            f"FOREACH (key IN KEYS($new_properties) | SET r[key] = $new_properties[key])\n"
        )
        parameters = {
            "new_properties": new_properties
        }
        with self.__driver.session() as session:
            session.run(
                query=query,
                parameters=parameters
            )
    
    def _delete_rela(
            self,
            r_id: str,
            pos: Tuple[str, str]
        ):
        from_m_id, to_m_id = pos
        query = (
            f"MATCH (p:memory {{ m_id: '{from_m_id}' }})\n"
            f"MATCH (q:memory {{ m_id: '{to_m_id}' }})\n"
            f"MATCH (p)-[r {{ r_id: '{r_id}' }}]->(q)\n"
            f"DELETE r\n"
        )
        with self.__driver.session() as session:
            session.run(
                query=query
            )

class Node:
    def __init__(self):
        self.__graph: Graph = None
        self.m_id = None
        self.label = None
        self._properties = None
        self._alive = False
        self._new_properties = {}
        self._removed_properties = []
        raise RuntimeError("Use Graph.create_node or Graph.match_node to get a Node instance")

    @classmethod
    def _create(cls, graph: Graph, m_id: int, label: str, properties: Dict[str, str | int | float]) -> 'Node':
        instance = cls.__new__(cls)
        instance.__graph = graph
        instance.m_id = m_id
        instance.label = label
        instance._properties = properties
        instance._alive = True
        instance._new_properties = {}
        instance._removed_properties = []
        
        return instance

    @staticmethod
    def ensure_alive(method):
        def wrapper(self, *args, **kwargs):
            if not getattr(self, '_alive', True):
                raise RuntimeError("This node was already removed from graph")
            return method(self, *args, **kwargs)
        return wrapper
    
    def __str__(self):
        return f"[{self.label}] {self._properties}"
    
    @ensure_alive
    def get_prop(self, key: str) -> str | int | float:
        return self._properties.get(key)
    
    @ensure_alive
    def set_prop(self, key: str, value: str | int | float):
        self._properties[key] = value
        self._new_properties[key] = value
    
    @ensure_alive
    def remove_prop(self, key: str):
        self._properties.pop(key)
        if key not in self._removed_properties:
            self._removed_properties.append(key)
    
    @ensure_alive
    def set_label(self, label: str):
        self.label = label
    
    @ensure_alive
    def update(self):
        self.__graph._update_node(
            m_id=self.m_id,
            new_label=self.label,
            new_properties=self._new_properties,
            removed_properties=self._removed_properties
        )
        self._new_properties = {}
        self._removed_properties = []
    
    @ensure_alive
    def create_rela(self, to: 'Node', label: str, properties: Dict[str, str | int | float]) -> 'Relationship':
        assert to._alive
        properties["r_id"] = uuid()
        from_m_id = self.m_id
        to_m_id = to.m_id
        return self.__graph._create_rela(
            pos=(from_m_id, to_m_id),
            label=label,
            properties=properties
        )
    
    @ensure_alive
    def _destroy(self):
        self.__graph._delete_node(self.m_id)
        self._alive = False

class Relationship:
    def __init__(self):
        self.__graph: Graph = None
        self.r_id = None
        self.pos = None
        self.label = None
        self._properties = None
        self._alive = False
        self._new_properties = {}
        self._removed_properties = []
        raise RuntimeError("Use Node.create_rela to get a Relationship instance")
    
    @staticmethod
    def ensure_alive(method):
        def wrapper(self, *args, **kwargs):
            if not getattr(self, '_alive', True):
                raise RuntimeError("This relationship was already removed from graph")
            return method(self, *args, **kwargs)
        return wrapper
    
    @classmethod
    def _create(cls, graph: Graph, r_id: str, pos: Tuple[str, str], label: str, properties: Dict[str, str | int | float]) -> 'Relationship':
        instance = cls.__new__(cls)
        instance.__graph = graph
        instance.r_id = r_id
        instance.pos = pos
        instance.label = label
        instance._properties = properties
        instance._alive = True
        instance._new_properties = {}
        instance._removed_properties = []
        
        return instance
    
    @ensure_alive
    def __str__(self):
        return f"[{self.label}] {self._properties}"
    
    @ensure_alive
    def get_prop(self, key: str) -> str | int | float:
        return self._properties.get(key)
    
    @ensure_alive
    def set_prop(self, key: str, value: str | int | float):
        self._properties[key] = value
        self._new_properties[key] = value
       
    @ensure_alive
    def remove_prop(self, key: str):
        self._properties.pop(key)
        if key not in self._removed_properties:
            self._removed_properties.append(key)
    
    @ensure_alive
    def set_label(self, label: str):
        self.label = label
    
    @ensure_alive
    def update(self):
        self.__graph.update_rela(
            r_id=self.r_id,
            pos=self.pos,
            new_properties=self._new_properties
        )
        
    @ensure_alive
    def destroy(self):
        self.__graph._delete_rela(
            r_id=self.r_id,
            pos=self.pos
        )
        self._alive = False