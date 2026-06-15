from database import get_connection
from datetime import datetime


class VehicleRepository:
    @staticmethod
    def create(plate_number, brand_model, vin_code, last_maintenance_mileage=0):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO vehicles (plate_number, brand_model, vin_code, last_maintenance_mileage, created_at) VALUES (?, ?, ?, ?, ?)",
            (plate_number, brand_model, vin_code, last_maintenance_mileage, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        vehicle_id = cursor.lastrowid
        conn.close()
        return vehicle_id

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(vehicle_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_plate(plate_number):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (plate_number,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(vehicle_id, **kwargs):
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [vehicle_id]
        cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    @staticmethod
    def update_last_mileage(vehicle_id, mileage):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE vehicles SET last_maintenance_mileage = ? WHERE id = ?", (mileage, vehicle_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(vehicle_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        conn.commit()
        conn.close()


class PartRepository:
    @staticmethod
    def create(name, code, price, stock=0, min_stock=5):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO parts (name, code, price, stock, min_stock, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, code, price, stock, min_stock, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        part_id = cursor.lastrowid
        conn.close()
        return part_id

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parts ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(part_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parts WHERE id = ?", (part_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_code(code):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parts WHERE code = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_stock(part_id, new_stock):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE parts SET stock = ? WHERE id = ?", (new_stock, part_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update(part_id, **kwargs):
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [part_id]
        cursor.execute(f"UPDATE parts SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    @staticmethod
    def get_low_stock():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parts WHERE stock < min_stock ORDER BY stock ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def delete(part_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM parts WHERE id = ?", (part_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def search(keyword):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM parts WHERE name LIKE ? OR code LIKE ?",
            (f'%{keyword}%', f'%{keyword}%')
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class PartTransactionRepository:
    @staticmethod
    def create(part_id, quantity, trans_type, order_id=None, note=None):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO parts_transactions (part_id, quantity, type, order_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (part_id, quantity, trans_type, order_id, note, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        txn_id = cursor.lastrowid
        conn.close()
        return txn_id

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pt.*, p.name as part_name, p.code as part_code
            FROM parts_transactions pt
            LEFT JOIN parts p ON pt.part_id = p.id
            ORDER BY pt.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_part_id(part_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pt.*, p.name as part_name, p.code as part_code
            FROM parts_transactions pt
            LEFT JOIN parts p ON pt.part_id = p.id
            WHERE pt.part_id = ?
            ORDER BY pt.created_at DESC
        ''', (part_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_date_range(start_date, end_date):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pt.*, p.name as part_name, p.code as part_code
            FROM parts_transactions pt
            LEFT JOIN parts p ON pt.part_id = p.id
            WHERE date(pt.created_at) BETWEEN date(?) AND date(?)
            ORDER BY pt.created_at DESC
        ''', (start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class FaultCodeRepository:
    @staticmethod
    def create(code, description, solution):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fault_codes (code, description, solution, created_at) VALUES (?, ?, ?, ?)",
            (code, description, solution, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        fc_id = cursor.lastrowid
        conn.close()
        return fc_id

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fault_codes ORDER BY code")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(fc_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fault_codes WHERE id = ?", (fc_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_code(code):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fault_codes WHERE code = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(fc_id, **kwargs):
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [fc_id]
        cursor.execute(f"UPDATE fault_codes SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    @staticmethod
    def delete(fc_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fault_codes WHERE id = ?", (fc_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def search(keyword):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM fault_codes WHERE code LIKE ? OR description LIKE ?",
            (f'%{keyword}%', f'%{keyword}%')
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class WorkOrderRepository:
    @staticmethod
    def create(vehicle_id, mileage, fault_description, fault_code_id=None, labor_cost=0, total_cost=0):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO work_orders (vehicle_id, mileage, fault_description, fault_code_id, labor_cost, total_cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (vehicle_id, mileage, fault_description, fault_code_id, labor_cost, total_cost, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()
        return order_id

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wo.*, v.plate_number, v.brand_model, fc.code as fault_code, fc.description as fault_desc
            FROM work_orders wo
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            LEFT JOIN fault_codes fc ON wo.fault_code_id = fc.id
            ORDER BY wo.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(order_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wo.*, v.plate_number, v.brand_model, fc.code as fault_code, fc.description as fault_desc, fc.solution as fault_solution
            FROM work_orders wo
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            LEFT JOIN fault_codes fc ON wo.fault_code_id = fc.id
            WHERE wo.id = ?
        ''', (order_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_vehicle_id(vehicle_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wo.*, v.plate_number, v.brand_model, fc.code as fault_code, fc.description as fault_desc
            FROM work_orders wo
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            LEFT JOIN fault_codes fc ON wo.fault_code_id = fc.id
            WHERE wo.vehicle_id = ?
            ORDER BY wo.created_at DESC
        ''', (vehicle_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_date_range(start_date, end_date):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wo.*, v.plate_number, v.brand_model, fc.code as fault_code, fc.description as fault_desc
            FROM work_orders wo
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            LEFT JOIN fault_codes fc ON wo.fault_code_id = fc.id
            WHERE date(wo.created_at) BETWEEN date(?) AND date(?)
            ORDER BY wo.created_at DESC
        ''', (start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def update_total_cost(order_id, total_cost):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE work_orders SET total_cost = ? WHERE id = ?", (total_cost, order_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(order_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM work_orders WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()


class WorkOrderPartRepository:
    @staticmethod
    def create(work_order_id, part_id, part_name, part_code, unit_price, quantity, subtotal):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO work_order_parts (work_order_id, part_id, part_name, part_code, unit_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (work_order_id, part_id, part_name, part_code, unit_price, quantity, subtotal)
        )
        conn.commit()
        wop_id = cursor.lastrowid
        conn.close()
        return wop_id

    @staticmethod
    def get_by_work_order_id(work_order_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM work_order_parts WHERE work_order_id = ?", (work_order_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def delete_by_work_order_id(work_order_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM work_order_parts WHERE work_order_id = ?", (work_order_id,))
        conn.commit()
        conn.close()


class PurchaseSuggestionRepository:
    @staticmethod
    def create(part_id, part_name, current_stock, suggested_quantity):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO purchase_suggestions (part_id, part_name, current_stock, suggested_quantity, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
            (part_id, part_name, current_stock, suggested_quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'PENDING')
        )
        conn.commit()
        ps_id = cursor.lastrowid
        conn.close()
        return ps_id

    @staticmethod
    def get_all(status=None):
        conn = get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM purchase_suggestions WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM purchase_suggestions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_pending():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchase_suggestions WHERE status = 'PENDING' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def update_status(ps_id, status):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE purchase_suggestions SET status = ? WHERE id = ?", (status, ps_id))
        conn.commit()
        conn.close()

    @staticmethod
    def exists_pending_for_part(part_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_suggestions WHERE part_id = ? AND status = 'PENDING'", (part_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
