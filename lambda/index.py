# lambda/index.py
import json
import urllib.request
import urllib.error
import urllib.parse
import os

# FastAPI エンドポイントURL
API_URL = "https://e214-35-247-23-37.ngrok-free.app/generate"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # FastAPIリクエスト用のペイロードを構築
        # 会話履歴があれば、そこから最後のメッセージを含めてコンテキストを提供
        prompt = message
        if conversation_history:
            # 会話の履歴を文字列として連結
            context = ""
            for msg in conversation_history:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    context += f"Q: {content}\n"
                elif role == "assistant":
                    context += f"A: {content}\n"
            prompt = f"{context}Q: {message}"
        
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512  # 必要に応じて調整
        }
        
        # HTTP POSTリクエストを準備
        headers = {
            "Content-Type": "application/json"
        }
        
        print("Calling FastAPI with payload:", json.dumps(request_payload))
        
        # FastAPI APIを呼び出し
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(request_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        # リクエストを送信し、レスポンスを取得
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            response_body = json.loads(response_data)
            print("FastAPI response:", json.dumps(response_body, default=str))
        
        # アシスタントの応答を取得 - generated_textキーを使用
        assistant_response = response_body.get('generated_text', '')
        
        # 応答の検証
        if not assistant_response:
            print("Warning: Empty response from model, checking alternative keys...")
            # 代替のキーをチェック
            assistant_response = response_body.get('response', '')
            if not assistant_response:
                print("Response body:", json.dumps(response_body))
                raise Exception("No valid response content found in the model output")
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except urllib.error.HTTPError as http_error:
        # HTTPエラーの詳細をログに記録
        error_message = f"HTTPエラー: {http_error.code} - {http_error.reason}"
        error_body = http_error.read().decode('utf-8')
        print(error_message)
        print(f"Error response body: {error_body}")
        
        if http_error.code == 429:
            error_message = "APIリクエスト制限に達しました。しばらく待ってから再度お試しください。"
        
        return {
            "statusCode": http_error.code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": error_message,
                "details": error_body if error_body else None
            })
        }
    except Exception as error:
        print("Error:", str(error))
        import traceback
        print(traceback.format_exc())
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }