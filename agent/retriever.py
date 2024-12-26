from shortuuid import uuid
from typing import (
    Dict, List, Tuple
)

from chromadb import PersistentClient
from utils.neo4j_orm import (
    Graph, Node, Relationship
)
from utils.logger import logger

class MemoryManager:
    def __init__(self):
        uri = "bolt://localhost:7687"
        username = "neo4j"
        password = "Yy030518neo4j"
        
        self.__graph = Graph(
            uri=uri,
            auth=(username, password)
        )
        
        chroma_client = PersistentClient()
        self.__collection = chroma_client.get_or_create_collection(
            name="memo_vec_db"
        )
    
    def __add_node_in_vec_db(self, m_id: str, abstract: str):
        self.__collection.add([m_id], documents=[abstract])
    
    def __del_node_in_vec_db(self, m_id: str):
        self.__collection.delete([m_id])
    
    def __add_node_in_graph(self, label: str, properties: Dict[str, str | int | float]) -> Node:
        node = self.__graph.create_node(label, properties)
        return node
    
    def __del_node_in_graph(self, node: Node):    
        node._destroy()

    def add_node(self, node_profile: Dict[str, str | int | float]) -> Node:
        for key in [
            "label",
            "abstract",
            "content"
        ]:
            if key not in node_profile:
                logger.error(f"MemoryManager::add_node : `{key}` not found in node profile")
                return None
        m_id = uuid()
        node_profile["m_id"] = m_id
        label = node_profile.pop("label")
        try:
            self.__add_node_in_vec_db(m_id)
        except Exception as e:
            logger.error(f"MemoryManager::add_node : One error occurred when adding a node : [{label}]\n{node_profile} -> {e}")
            return None
        try:
            node = self.__add_node_in_graph(label, node_profile)
            logger.info(f"MemoryManager::add_node : successfully added node : {node}")
            return node
        except Exception as e:
            # Rollback
            logger.error(f"MemoryManager::add_node : One error occurred when adding a node : [{label}]\n{node_profile} -> {e}")
            self.__del_node_in_vec_db(m_id)
            logger.info(f"MemoryManager::add_node : rollback... deleted node(mid = {m_id}) in vector DB.")
            return None
    
    def del_node(self, node: Node) -> bool:
        pass
    
    def match_node(self, node_profile: Dict[str, str | int | float]) -> List[Node]:
        pass
    
    
        