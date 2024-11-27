from neo4j import GraphDatabase
from chromadb import PersistentClient

from shortuuid import uuid
from datetime import datetime

from typing_extensions import List, Dict, Tuple
import logging

from pathlib import Path
import re

class Memory:
    def __init__(self):
        uri = "bolt://localhost:7687"
        username = "neo4j"
        password = "Yy030518neo4j"
        self.driver = GraphDatabase.driver(uri, auth=(username, password)) # GraphDB
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        self.logger.addHandler(console_handler)
        
        log_path = Path('logs') / "memory"
        file_handler = logging.FileHandler(log_path / f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        chroma_client = PersistentClient()
        self.collection = chroma_client.get_or_create_collection(
            name="memo_vec_db"
        ) # VectorDB
    
    def __add_item_in_vec_db(self, m_item: dict) -> bool:
        try:
            self.collection.add(
                ids=[m_item["m_id"]],
                documents=[m_item["abstract"]]
            )
            self.logger.info(msg=f"Added memory item: {str(m_item)} in vectorDB")
            return True
        except Exception as e:
            self.logger.error(msg=f"Error occurred when adding memory item: {str(m_item)} in vectorDB: {e}")
        
        return False
    
    def __query_item_in_vec_db(self, q_text: str, n_results) -> List[Tuple]:
        try:
            result = self.collection.query(
                query_texts=[q_text],
                n_results=n_results
            )
            self.logger.info(msg=f"Query: ({q_text}) succeeded!")
            return list(zip(result['ids'][0], result["documents"][0]))
        except Exception as e:
            self.logger.error(msg=f"Error occurred when querying: {q_text}, n_results = {n_results}: {e}")
    
    def __del_item_in_vec_db(self, m_id: str) -> bool:
        try:
            self.collection.delete(
                ids=[m_id]
            )
            self.logger.info(msg=f"Deleted memory item (m_id = {m_id}) in vectorDB")
            return True
        except Exception as e:
            self.logger.error(msg=f"Error occurred when deleting memory item (m_id = {m_id}) in vectorDB: {str(e)}")
        
        return False
    
    def __add_item_in_graph_db(self, m_item: dict) -> bool:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        m_item["creation_time"] = timestamp
        m_item["update_time"] = timestamp
        cql_query = f"""
        CREATE ( m_item:memory:{m_item["label"]} {{
            m_id: $m_id,
            creation_time: $creation_time,
            update_time: $update_time,
            abstract: $abstract,
            content: $content,
            familiarity: $familiarity,
            note: $note
        }} )
        """
        cql_parameters = { key: m_item.get(key) for key in [
            "m_id",
            "creation_time",
            "update_time",
            "abstract",
            "content",
            "familiarity",
            "note"
        ] }
        try:
            with self.driver.session() as session:
                session.run(
                    query=cql_query,
                    parameters=cql_parameters
                )
            self.logger.info(msg=f"Added memory item: {str(m_item)} in graphDB")
            return True
        except Exception as e:
            self.logger.error(msg=f"Error occurred when adding memory item: {str(m_item)} in graphDB: {str(e)}")
        return False
    
    def __update_item_in_graph_db(self, m_id: str, update_item: dict) -> bool:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        update_item["update_time"] = timestamp
        cql_query = """
        MATCH (m:memory { m_id: $m_id })
        FOREACH (key IN keys($update_item) |
            SET m[key] = $update_item[key]
        )
        """
        cql_parameters = {
            "m_id": m_id,
            "update_item": update_item
        }
        try:
            with self.driver.session() as session:
                session.run(
                    query=cql_query,
                    parameters=cql_parameters
                )
            self.logger.info(msg=f"Successfully updated a memory item, updated entry: {update_item}")
            return True
        except Exception as e:
            self.logger.error(msg=f"An error occured when updating memory item (m_id = {m_id}): {e}")
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
            self.logger.info(msg=f"Deleted memory item (m_id = {m_id}) in graphDB")
            return True
        except Exception as e:
            self.logger.error(msg=f"Error occurred when deleting memory item (m_id = {m_id}) in graphDB: {str(e)}")
        
        return False

    def __lookup_item_in_graph_db(self, m_id: str) -> dict:
        cql_query = """
        MATCH (m { m_id: $m_id } )
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
                item = result.single()['m']
                m_item = dict(item)
                for label in item.labels:
                    if label != "memory":
                        m_item['label'] = label
                self.logger.info(msg=f"Found m_item (m_id = {m_id}): {str(m_item)}")
                return m_item
        except Exception as e:
            # tb = e.__traceback__
            # file_name = tb.tb_frame.f_code.co_filename
            # line_number = tb.tb_lineno
            self.logger.error(msg=f"Error ocurred when looking up m_item (m_id = {m_id}): {e}")
        return {}
                

    def __add_rela_in_graph_db(self, m1_id: str, m2_id: str, rela: dict) -> bool:
        for key in ["label", "content"]:
            if key not in rela:
                self.logger.error(f"Key {key} not found in relationship!")
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
            self.logger.info(msg=f"Added relationship {rela} between m1(id = {m1_id}) and m2(id = {m2_id})")
            return True
        except Exception as e:
            self.logger.error(msg=f"An Error occurred when adding relationship {rela} between m1(id = {m1_id}) and m2(id = {m2_id}): {e}")
        return False
        
    def add_item(self, m_item: dict) -> str | None:
        for key in ["label", "abstract", "content"]:
            if key not in m_item:
                self.logger.error(msg=f"Key {key} not found in m_item!")
                return False
        m_id = uuid()
        m_item["m_id"] = m_id
        try:
            self.__add_item_in_vec_db(m_item)
            if not self.__add_item_in_graph_db(m_item):
                # Roll back
                self.__del_item_in_vec_db(m_id)
                return None
            return m_id
        except Exception as e:
            self.logger.error(f"An error occurred when adding memory item: {str(m_item)}")
        
        return None

    def add_rela(self, m1_id: str, m2_id, rela: dict) -> bool:
        return self.__add_rela_in_graph_db(m1_id=m1_id, m2_id=m2_id, rela=rela)

    def update(self, m_id: str, update_item: Dict) -> bool:
        return self.__update_item_in_graph_db(m_id=m_id, update_item=update_item)
    
    def del_item(self, m_id: str) -> bool:
        self.__del_item_in_vec_db(m_id)
        if not self.__del_item_in_graph_db(m_id):
            # Roll back
            m_item = self.__lookup_item_in_graph_db(m_id)
            self.__add_item_in_vec_db(m_item)
            return False

        return True
    
    def query(self, q_text: str, n_results) -> List[Dict]:
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
            self.logger.info(msg="All items was removed!")
        except Exception as e:
            pass