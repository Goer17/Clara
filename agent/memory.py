from neo4j import GraphDatabase
from chromadb import PersistentClient

from shortuuid import uuid
from datetime import datetime

from typing_extensions import List, Dict, Tuple

from utils.logger import logger

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
        try:
            self.collection.add(
                ids=[m_item["m_id"]],
                documents=[m_item["abstract"]]
            )
            logger.info(msg=f"Added memory item: {str(m_item)} in vectorDB")
            return True
        except Exception as e:
            logger.error(msg=f"Error occurred when adding memory item: {str(m_item)} in vectorDB: {e}")
        
        return False
    
    def __query_item_in_vec_db(self, q_text: str, n_results) -> List[Tuple]:
        try:
            result = self.collection.query(
                query_texts=[q_text],
                n_results=n_results
            )
            logger.info(msg=f"Query: ({q_text}) succeeded!")
            return list(zip(result['ids'][0], result["documents"][0]))
        except Exception as e:
            logger.error(msg=f"Error occurred when querying: {q_text}, n_results = {n_results}: {e}")
    
    def __del_item_in_vec_db(self, m_id: str) -> bool:
        try:
            self.collection.delete(
                ids=[m_id]
            )
            logger.info(msg=f"Deleted memory item (m_id = {m_id}) in vectorDB")
            return True
        except Exception as e:
            logger.error(msg=f"Error occurred when deleting memory item (m_id = {m_id}) in vectorDB: {str(e)}")
        
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
            logger.info(msg=f"Added memory item: {str(m_item)} in graphDB")
            return True
        except Exception as e:
            logger.error(msg=f"Error occurred when adding memory item: {str(m_item)} in graphDB: {str(e)}")
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
            logger.info(msg=f"Successfully updated a memory item, updated entry: {update_item}")
            return True
        except Exception as e:
            logger.error(msg=f"An error occured when updating memory item (m_id = {m_id}): {e}")
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
            logger.info(msg=f"Deleted memory item (m_id = {m_id}) in graphDB")
            return True
        except Exception as e:
            logger.error(msg=f"Error occurred when deleting memory item (m_id = {m_id}) in graphDB: {str(e)}")
        
        return False

    def __lookup_item_in_graph_db(self, m_id: str) -> Dict:
        cql_query = """
        MATCH (m:memory { m_id: $m_id } )
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
                logger.info(msg=f"Found m_item (m_id = {m_id}): {str(m_item)}")
                return m_item
        except Exception as e:
            logger.error(msg=f"Error ocurred when looking up m_item (m_id = {m_id}): {e}")
        return {}
    
    def __lookup_neighbors_in_graph_db(self, m_id: str, limit: int = 5) -> List[Dict]:
        cql_query = """
        MATCH (m:memory { m_id: $m_id })
        MATCH (i)-[r]-(m)
        RETURN i, r
        LIMIT $limit
        """
        cql_parameters = {
            "m_id": m_id,
            "limit": limit
        }
        try:
            with self.driver.session() as session:
                results = session.run(
                    query=cql_query,
                    parameters=cql_parameters
                )
                ans = []
                for result in results:
                    o_item = result["i"]
                    o_rela = result["r"]

                    m_item = dict(o_item)
                    for label in o_item.labels:
                        if label != "memory":
                            m_item["label"] = label
                    rela = dict(o_rela)
                    rela["label"] = o_rela.type
                    ans.append(
                        {
                            "m_item": m_item,
                            "rela": rela
                        }
                    )
                return ans
        except Exception as e:
            logger.error(msg=f"An error occurred when searching the neibour of node (m_id = {m_id}): {e}")
        return []

    def __add_rela_in_graph_db(self, m1_id: str, m2_id: str, rela: dict) -> bool:
        for key in ["label", "content"]:
            if key not in rela:
                logger.error(f"Key {key} not found in relationship!")
                return False
        label = rela["label"]
        content = rela["content"]
        cql_query = f"""
        MATCH (m1 {{ m_id: $m1_id }})
        MATCH (m2 {{ m_id: $m2_id }})
        CREATE (m1)-[:{label} {{ content: $content }}]->(m2)
        """
        try:
            with self.driver.session() as session:
                session.run(
                    query=cql_query,
                    parameters={
                        "m1_id": m1_id,
                        "m2_id": m2_id,
                        "content": content
                    }
                )
            logger.info(msg=f"Added relationship {rela} between m1(id = {m1_id}) and m2(id = {m2_id})")
            return True
        except Exception as e:
            logger.error(msg=f"An Error occurred when adding relationship {rela} between m1(id = {m1_id}) and m2(id = {m2_id}): {e}")
        return False
    
    def __lookup_same_label(self, label: str, limit: int = 25, order: Dict | None = None) -> List[Dict] | None:
        if order:
            for key in ["by", "method"]:
                if key not in order:
                    logger.error(f"Key {key} not found in order: {order}")
                    return None
            if order["method"] not in ["asc", "desc"]:
                logger.error(f"method can only be 'asc' or 'desc'\n")
                return None
        cql_query = f"""
        MATCH (m:{label})
        RETURN m
        """
        if order:
            cql_query += f"""
            ORDER BY m.{order["by"]} {order["method"].upper()}
            """
        cql_query += f"LIMIT {limit}"
        try:
            with self.driver.session() as session:
                records = session.run(
                    query=cql_query
                )
                results = []
                for record in records:
                    o_item = record["m"]
                    m_item = dict(o_item)
                    m_item["label"] = label
                    results.append(m_item)
                logger.info(msg=f"{len(results)} m_items were successfully retrieved!")
                return results
        except Exception as e:
            logger.error(msg=f"An error occurred when searching the memory item with label `{label}` : {e}")
        return None
        
    def add_item(self, m_item: dict) -> str | None:
        for key in ["label", "abstract", "content"]:
            if key not in m_item:
                logger.error(msg=f"Key {key} not found in m_item!")
                return None
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
            logger.error(f"An error occurred when adding memory item: {str(m_item)}")
        
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
    
    def lookup(self, m_id: str) -> Dict:
        return self.__lookup_item_in_graph_db(m_id=m_id)
    
    def lookup_with_neighbors(self, m_id: str, limit: int = 5) -> Tuple[Dict, List[Dict]]:
        m_item = self.__lookup_item_in_graph_db(m_id=m_id)
        neighbors = self.__lookup_neighbors_in_graph_db(m_id=m_id, limit=limit)
        
        return m_item, neighbors
    
    def lookup_same_label(self, label: str, limit: int = 25, order: Dict | None = None) -> List[Dict] | None:
        return self.__lookup_same_label(label=label, limit=limit, order=order)
    
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
            logger.info(msg="All items in graphDB were removed!")
            logger.info(msg="All items were removed!")
        except Exception as e:
            logger.error(msg="An error were occurred when removing all memory items")
    
    @staticmethod
    def decode_m_item(m_item: Dict) -> str | None:
        for key in ["label", "abstract", "content"]:
            if key not in m_item:
                logger.error(msg=f"Key {key} not found in m_item!")
                return None
        string = (
            f"label: {m_item['label']}\n"
            f"abstract: {m_item['abstract']}\n"
            f"content:\n{m_item['content']}"
        )
        
        return string