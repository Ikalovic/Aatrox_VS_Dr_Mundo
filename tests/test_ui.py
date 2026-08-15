def test_root_has_game_shell(client):
    response=client.get("/")
    assert response.status_code == 200
    assert b"Aatrox VS Dr. Mundo" in response.data
