import krpc

SERVER_IP = "192.168.1.25"  # IP de ton KSP / KRPC
SERVER_PORT = 50008          # port par défaut kRPC
SERVER_STREAM_PORT = 50001   # port par défaut pour le streaming

def main():
    try:
        print(f"Connexion à kRPC sur {SERVER_IP}…")
        conn = krpc.connect(
            name="Test Connection",
            address=SERVER_IP,
            rpc_port=SERVER_PORT,
            stream_port=SERVER_STREAM_PORT
        )
        print("✅ Connexion réussie !")
        print("Version kRPC du serveur :", conn.krpc.get_status().version)
        conn.close()
    except Exception as e:
        print("❌ Échec de connexion :", e)

if __name__ == "__main__":
    main()
