import chromadb
 

# 向量資料庫路徑
path = "./chroma"

def init_db_client():
    """初始化資料庫"""
    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client
 
def create_collection(collection_name):
    """創建collection"""
    chroma_client = init_db_client()
    collection=chroma_client.get_or_create_collection(name=collection_name)
    return collection

def add_document(collection, document, id, metadata):
    """新增單筆資料"""
    collection.add(
        documents=document,
        ids=id,
        metadatas=metadata
    )

def get_all_documents(collection):
    """查詢所有資料"""
    return collection.get()

def get_document(collection, id):
    """查詢單筆資料"""
    return collection.get(id)
    
def update_document(collection, id, document, metadata):
    """更新資料"""
    collection.upsert(
        ids=[id],
        documents=document,
        metadatas=metadata
    )
    
def delete_document(collection, id):
    """刪除資料"""
    collection.delete(id)

def query(collection, query_texts, n_results):
    """檢索資料"""
    return collection.query(
        query_texts=query_texts,
        n_results=n_results
    )
def retrive_n_results(user_id, query_texts, n_results=3):
    """檢索資料"""
    collection_name = f"collection_{user_id}"
    collection = create_collection(collection_name)
    results = query(collection, query_texts, n_results)["documents"]  # 獲取檢索結果中的文檔內容
    
    # print("Results type:", type(results))  # 檢查 results 的類型
    # print("First item type:", type(results[0]))  # 檢查第一個項目的類型
    
    # 如果 results 是巢狀列表，先展平它
    if isinstance(results, list) and any(isinstance(item, list) for item in results):
        flattened_results = [item for sublist in results for item in sublist]
        content = "\n".join(str(text) for text in flattened_results)
    else:
        content = "\n".join(str(text) for text in results)
    
    return content

# print(retrive_n_results(57, "文化日活動",1))