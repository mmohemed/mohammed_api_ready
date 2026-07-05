# =========================================
# اختبارات نظام Smart Factory ERP
# =========================================


# ---------- الأساسيات واللوحة ----------
class TestBasics:
    def test_dashboard_html_at_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Smart Factory ERP" in response.text

    def test_api_info(self, client):
        assert client.get("/api/info").status_code == 200

    def test_dashboard_kpis(self, client):
        data = client.get("/dashboard").json()
        assert data["inventory"]["products_count"] >= 4
        assert data["machines"]["total"] >= 3

    def test_sales_timeseries(self, client):
        data = client.get("/dashboard/sales-timeseries?days=30").json()
        assert data["series"], "يجب أن توجد مبيعات يومية في بيانات seed"


# ---------- المصادقة والصلاحيات ----------
class TestAuth:
    def test_bad_login_rejected(self, client):
        response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401

    def test_write_without_token_rejected(self, client):
        response = client.post("/inventory/products", json={"name": "x", "sku": "NOAUTH"})
        assert response.status_code == 401

    def test_garbage_token_rejected(self, client):
        response = client.post("/employees", json={"name": "x"},
                               headers={"Authorization": "Bearer abc.def"})
        assert response.status_code == 401

    def test_viewer_cannot_write(self, client, admin_headers):
        client.post("/auth/register", headers=admin_headers, json={
            "username": "viewer_t", "password": "secret1", "role": "viewer"})
        login = client.post("/auth/login", json={"username": "viewer_t", "password": "secret1"})
        viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/inventory/products", headers=viewer_headers).status_code == 200
        assert client.post("/employees", headers=viewer_headers,
                           json={"name": "x"}).status_code == 403

    def test_admin_lists_users(self, client, admin_headers):
        assert client.get("/auth/users", headers=admin_headers).status_code == 200


# ---------- المخزون ----------
class TestInventory:
    def test_create_and_duplicate_sku(self, client, admin_headers):
        product = {"name": "منتج اختبار", "sku": "TST-1", "quantity": 50, "unit_price": 9}
        assert client.post("/inventory/products", headers=admin_headers, json=product).status_code == 200
        assert client.post("/inventory/products", headers=admin_headers, json=product).status_code == 400

    def test_over_withdraw_rejected(self, client, admin_headers):
        response = client.post("/inventory/products/1/adjust", headers=admin_headers,
                               json={"change": -999999})
        assert response.status_code == 400

    def test_alerts(self, client):
        data = client.get("/inventory/alerts").json()
        assert "alerts" in data


# ---------- تعديل وحذف (CRUD) ----------
class TestCrud:
    def test_update_product(self, client, admin_headers):
        created = client.post("/inventory/products", headers=admin_headers, json={
            "name": "قبل التعديل", "sku": "UPD-1", "quantity": 10}).json()
        updated = client.put(f"/inventory/products/{created['id']}", headers=admin_headers,
                             json={"name": "بعد التعديل", "unit_price": 99}).json()
        assert updated["name"] == "بعد التعديل" and updated["unit_price"] == 99
        assert updated["quantity"] == 10  # الكمية لا تتغير من التعديل

    def test_delete_product_without_moves(self, client, admin_headers):
        created = client.post("/inventory/products", headers=admin_headers, json={
            "name": "للحذف", "sku": "DEL-1"}).json()
        assert client.delete(f"/inventory/products/{created['id']}",
                             headers=admin_headers).status_code == 200
        assert client.get(f"/inventory/products/{created['id']}").status_code == 404

    def test_delete_product_with_sales_blocked(self, client, admin_headers):
        # المنتج 1 له مبيعات في seed — يجب رفض حذفه
        assert client.delete("/inventory/products/1", headers=admin_headers).status_code == 400

    def test_update_machine(self, client, admin_headers):
        created = client.post("/machines", headers=admin_headers, json={"name": "آلة قبل"}).json()
        updated = client.put(f"/machines/{created['id']}", headers=admin_headers,
                             json={"name": "آلة بعد", "status": "stopped"}).json()
        assert updated["name"] == "آلة بعد" and updated["status"] == "stopped"

    def test_delete_machine_without_orders(self, client, admin_headers):
        created = client.post("/machines", headers=admin_headers, json={"name": "آلة للحذف"}).json()
        assert client.delete(f"/machines/{created['id']}", headers=admin_headers).status_code == 200

    def test_delete_machine_with_orders_blocked(self, client, admin_headers):
        # الآلة 1 لها أوامر إنتاج في seed
        assert client.delete("/machines/1", headers=admin_headers).status_code == 400

    def test_update_employee(self, client, admin_headers):
        created = client.post("/employees", headers=admin_headers,
                              json={"name": "موظف", "salary": 1000}).json()
        updated = client.put(f"/employees/{created['id']}", headers=admin_headers,
                             json={"salary": 2000}).json()
        assert updated["salary"] == 2000 and updated["name"] == "موظف"

    def test_crud_requires_writer(self, client):
        assert client.put("/inventory/products/1", json={"name": "x"}).status_code == 401
        assert client.delete("/machines/1").status_code == 401


# ---------- الآلات والصيانة التنبؤية ----------
class TestMachines:
    def test_risk_overview(self, client):
        machines = client.get("/machines/risk-overview").json()["machines"]
        assert machines and all("risk_level" in m for m in machines)

    def test_stressed_machine_high_risk(self, client):
        # الآلة 2 في بيانات seed مجهدة عمدًا (حرارة واهتزاز مرتفعان)
        data = client.get("/machines/2/predict-failure").json()
        assert data["failure_probability"] > 0.5

    def test_healthy_machine_low_risk(self, client):
        data = client.get("/machines/1/predict-failure").json()
        assert data["failure_probability"] < 0.4

    def test_missing_machine_404(self, client):
        assert client.get("/machines/999/predict-failure").status_code == 404


# ---------- الإنتاج والمبيعات ----------
class TestProductionAndSales:
    def test_production_cycle_adds_to_stock(self, client, admin_headers):
        before = client.get("/inventory/products/1").json()["quantity"]
        order = client.post("/production/orders", headers=admin_headers,
                            json={"product_id": 1, "machine_id": 1, "planned_quantity": 100}).json()
        client.post(f"/production/orders/{order['id']}/complete", headers=admin_headers,
                    json={"produced_quantity": 90, "defective_quantity": 5})
        after = client.get("/inventory/products/1").json()["quantity"]
        assert after == before + 85  # الصافي = المنتَج - المعيب

    def test_quality_anomalies(self, client):
        data = client.get("/production/quality/anomalies").json()
        assert data["status"] == "ok"
        assert data["anomalies_found"] >= 2  # أمران شاذان مزروعان في seed

    def test_oversell_rejected(self, client, admin_headers):
        response = client.post("/sales/orders", headers=admin_headers,
                               json={"product_id": 1, "quantity": 10**9})
        assert response.status_code == 400

    def test_sale_deducts_stock(self, client, admin_headers):
        before = client.get("/inventory/products/1").json()["quantity"]
        client.post("/sales/orders", headers=admin_headers, json={"product_id": 1, "quantity": 5})
        after = client.get("/inventory/products/1").json()["quantity"]
        assert after == before - 5

    def test_demand_forecast(self, client):
        data = client.get("/sales/forecast/1?days_ahead=30").json()
        assert data["status"] == "ok"
        assert data["expected_total_demand"] > 0


# ---------- الذكاء الاصطناعي ----------
class TestAI:
    def test_assistant_fallback_engine(self, client):
        data = client.post("/ai/assistant", json={"question": "كيف حال المخزون؟"}).json()
        assert data["engine"] == "rules"
        assert data["answer"]

    def test_assistant_topics(self, client):
        for question in ["هل توجد أعطال في الآلات؟", "كم إيرادات المبيعات؟", "ما وضع الإنتاج؟"]:
            data = client.post("/ai/assistant", json={"question": question}).json()
            assert data["answer"]

    def test_insights_sorted_by_priority(self, client):
        data = client.get("/ai/insights").json()
        assert data["insights_count"] >= 1
        priorities = [i["priority"] for i in data["insights"]]
        assert priorities == sorted(priorities)

    def test_insights_include_maintenance(self, client):
        data = client.get("/ai/insights").json()
        assert any(i["category"] == "صيانة" for i in data["insights"])


# ---------- إنترنت الأشياء ----------
class TestIoT:
    def test_parse_topic(self):
        from erp.iot.mqtt_ingest import parse_topic_machine_id
        assert parse_topic_machine_id("factory/machines/3/sensors") == 3
        assert parse_topic_machine_id("factory/other/3/sensors") is None
        assert parse_topic_machine_id("factory/machines/abc/sensors") is None

    def test_ingest_valid_reading(self, client):
        from erp.iot.mqtt_ingest import ingest_reading
        result = ingest_reading(
            "factory/machines/1/sensors",
            b'{"temperature": 71, "vibration": 2.5, "pressure": 5.1, "running_hours": 210}',
        )
        assert result["status"] == "ok"

    def test_ingest_rejects_bad_payload(self):
        from erp.iot.mqtt_ingest import ingest_reading
        assert ingest_reading("factory/machines/1/sensors", b"not json")["status"] == "error"
        assert ingest_reading("factory/machines/1/sensors", b'{"temperature": 70}')["status"] == "error"

    def test_ingest_rejects_unknown_machine(self):
        from erp.iot.mqtt_ingest import ingest_reading
        result = ingest_reading(
            "factory/machines/999/sensors",
            b'{"temperature": 70, "vibration": 2, "pressure": 5, "running_hours": 10}',
        )
        assert result["status"] == "error"

    def test_listener_off_without_env(self):
        from erp.iot.mqtt_ingest import start_mqtt_listener
        assert start_mqtt_listener() is False
