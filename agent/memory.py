from neo4j import GraphDatabase
from chromadb import PersistentClient

from shortuuid import uuid
from datetime import datetime

from typing_extensions import List, Dict

class Memory:
    def __init__(self):
        uri = "bolt://localhost:7687"
        username = "neo4j"
        password = "Yy030518neo4j"
        self.driver = GraphDatabase.driver(uri, auth=(username, password)) # GraphDB

        chroma_client = PersistentClient()
        self.collection = chroma_client.get_or_create_collection(
            name="memo_vec_db"
        ) # VectorDB
    
    def __add_item_in_vec_db(self, m_item: dict) -> bool:
        for key in ["m_id", "abstract"]:
            if key not in m_item:
                print(f"Key {key} not found in m_item!")
        try:
            self.collection.add(
                ids=[m_item["m_id"]],
                documents=[m_item["abstract"]]
            )
            return True
        except Exception as e:
            print(e)
        
        return False
    
    def __query_item_in_vec_db(self, q_text: str, n_results) -> List[Dict]:
        try:
            result = self.collection.query(
                query_texts=[q_text],
                n_results=n_results
            )
            return zip(result['ids'][0], result["documents"][0])
        except Exception as e:
            print(e)
    
    def __del_item_in_vec_db(self, m_id: str) -> bool:
        try:
            self.collection.delete(
                ids=[m_id]
            )
            return True
        except Exception as e:
            print(e)
        
        return False
    
    def __add_item_in_graph_db(self, m_item: dict) -> bool:
        for key in ["m_id", "label", "abstract", "content"]:
            if key not in m_item:
                print(f"Key {key} not found in m_item!")
                return False
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        m_item["timestamp"] = timestamp
        cql_query = f"""
        CREATE ( m_item:memory:{m_item["label"]} {{
            m_id: $m_id,
            timestamp: $timestamp,
            abstract: $abstract,
            content: $content,
            note: $note
        }} )
        """
        cql_parameters = { key: m_item.get(key) for key in [
            "m_id",
            "timestamp",
            "abstract",
            "content",
            "note"
        ] }
        try:
            with self.driver.session() as session:
                session.run(
                    query=cql_query,
                    parameters=cql_parameters
                )
                return True
        except Exception as e:
            print(e)
        
        return False
        
    
    def __del_item_in_graph_db(self, m_id: str) -> bool:
        cql_query = """
        MATCH (m { m_id: $m_id } )
        DETACH DELETE m
        """
        cql_parameters = {
            "m_id": m_id
        }
        try:
            with self.driver.session() as session:
                session.run(
                    query=cql_query,
                    parameters=cql_parameters
                )
            return True
        except Exception as e:
            print(e)
        
        return False

    def __lookup_item_in_graph_db(self, m_id: str) -> dict:
        cql_query = """
        MATCH (m { m_id: $m_id} )
        RETURN m
        """
        cql_paramters = {
            "m_id": m_id
        }
        try:
            with self.driver.session() as session:
                result = session.run(
                    query=cql_query,
                    parameters=cql_paramters
                )
                return [record.data() for record in result][0]['m']
        except Exception as e:
            print(e)
        return {}
                

    def __add_rela_in_graph_db(self, m1_id: str, m2_id: str, rela: dict) -> bool:
        for key in ["label", "content"]:
            if key not in rela:
                print(f"Key {key} not found in relationship!")
        label = rela["label"]
        content = rela["content"]
        cql_query = f"""
        MATCH (m1 {{ m_id: $m1_id }})
        MATCH (m2 {{ m_id: $m2_id }})
        CREATE (m1)-[:{label} {{ content: $content }}]->(m2)
        """
        try:
            with self.driver.session() as session:
                res = session.run(
                    query=cql_query,
                    parameters={
                        "m1_id": m1_id,
                        "m2_id": m2_id,
                        "content": content
                    }
                )
                return True
        except Exception as e:
            # TODO
            print(e)
        
        return False
        
    def add_item(self, m_item: dict) -> str:
        m_id = uuid()
        m_item["m_id"] = m_id
        try:
            self.__add_item_in_vec_db(m_item)
            if not self.__add_item_in_graph_db(m_item):
                # Roll back
                self.__del_item_in_vec_db(m_id)
                return ""
            return m_id
        except Exception as e:
            # TODO
            print(e)
        
        return ""

    def add_rela(self, m1_id: str, m2_id, rela: dict) -> bool:
        return self.__add_rela_in_graph_db(m1_id=m1_id, m2_id=m2_id, rela=rela)

    def del_item(self, m_id: str) -> bool:
        self.__del_item_in_vec_db(m_id)
        if not self.__del_item_in_graph_db(m_id):
            # Roll back
            m_item = self.__lookup_item_in_graph_db(m_id)
            self.__add_item_in_vec_db(m_item)
            return False

        return True
    
    def query(self, q_text: str, n_results: int = 5) -> List[Dict]:
        return self.__query_item_in_vec_db(q_text=q_text, n_results=n_results)
    
    def lookup(self, m_id: str) -> dict:
        return self.__lookup_item_in_graph_db(m_id=m_id)
    
    def clear_all(self):
        """
        Clear all memory
        """
        try:
            m_ids = self.collection.get()["ids"]
            for m_id in m_ids:
                self.__del_item_in_vec_db(m_id)
            with self.driver.session() as session:
                session.run(
                    query="""
                    MATCH (n) DETACH DELETE n
                    """
                )
        except Exception as e:
            print(e)