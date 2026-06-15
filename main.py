import sys
from database import init_db, seed_sample_data, MAINTENANCE_INTERVAL
from services import (
    VehicleService, PartService, FaultCodeService,
    WorkOrderService, PurchaseSuggestionService
)
from reports import (
    export_parts_transactions, export_revenue_report,
    generate_history_report, save_history_report
)


def print_header(title):
    width = 60
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)


def print_menu(options):
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print(f"  0. 返回上级")
    print()


def input_prompt(prompt, default=None, required=False):
    while True:
        if default is not None:
            val = input(f"{prompt} [{default}]: ").strip()
            if val == "":
                return default
        else:
            val = input(f"{prompt}: ").strip()
        if not required or val:
            return val
        print("  该项不能为空，请重新输入。")


def input_float(prompt, default=None, required=False):
    while True:
        val = input_prompt(prompt, default, required)
        if val == "" and not required:
            return 0.0
        try:
            return float(val)
        except ValueError:
            print("  请输入有效的数字。")


def input_int(prompt, default=None, required=False, min_value=0):
    while True:
        val = input_prompt(prompt, default, required)
        if val == "" and not required:
            return 0
        try:
            num = int(val)
            if num >= min_value:
                return num
            print(f"  请输入大于等于 {min_value} 的整数。")
        except ValueError:
            print("  请输入有效的整数。")


# ========== 车辆管理 ==========
def vehicle_menu():
    while True:
        print_header("车辆档案管理")
        print_menu(["新增车辆档案", "查看所有车辆", "按车牌号查询", "修改车辆信息", "删除车辆"])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("新增车辆档案")
            plate = input_prompt("车牌号", required=True)
            brand = input_prompt("品牌型号", required=True)
            vin = input_prompt("VIN码", required=True)
            mileage = input_int("上次保养里程(km)", default=0)
            vid, err = VehicleService.add_vehicle(plate, brand, vin, mileage)
            if err:
                print(f"\n  错误: {err}")
            else:
                print(f"\n  车辆档案创建成功，ID: {vid}")
            input("\n按回车继续...")

        elif choice == "2":
            print_header("所有车辆列表")
            vehicles = VehicleService.list_vehicles()
            if not vehicles:
                print("  暂无车辆档案")
            else:
                print(f"  {'ID':<6}{'车牌号':<14}{'品牌型号':<20}{'VIN码':<20}{'上次保养里程'}")
                print("  " + "-" * 72)
                for v in vehicles:
                    print(f"  {v['id']:<6}{v['plate_number']:<14}{v['brand_model']:<20}"
                          f"{v['vin_code']:<20}{v['last_maintenance_mileage']} km")
            input("\n按回车继续...")

        elif choice == "3":
            print_header("按车牌号查询")
            plate = input_prompt("请输入车牌号", required=True)
            v = VehicleService.find_vehicle_by_plate(plate)
            if not v:
                print(f"\n  未找到车牌号为 {plate} 的车辆")
            else:
                print(f"\n  ID:         {v['id']}")
                print(f"  车牌号:     {v['plate_number']}")
                print(f"  品牌型号:   {v['brand_model']}")
                print(f"  VIN码:      {v['vin_code']}")
                print(f"  上次保养:   {v['last_maintenance_mileage']} km")
                print(f"  建档时间:   {v['created_at']}")
            input("\n按回车继续...")

        elif choice == "4":
            print_header("修改车辆信息")
            plate = input_prompt("请输入车牌号", required=True)
            v = VehicleService.find_vehicle_by_plate(plate)
            if not v:
                print(f"\n  未找到车牌号为 {plate} 的车辆")
                input("\n按回车继续...")
                continue
            brand = input_prompt("品牌型号", default=v['brand_model'])
            vin = input_prompt("VIN码", default=v['vin_code'])
            mileage = input_int("上次保养里程(km)", default=v['last_maintenance_mileage'])
            VehicleService.update_vehicle(v['id'], brand_model=brand, vin_code=vin, last_maintenance_mileage=mileage)
            print("\n  车辆信息已更新")
            input("\n按回车继续...")

        elif choice == "5":
            print_header("删除车辆")
            plate = input_prompt("请输入车牌号", required=True)
            v = VehicleService.find_vehicle_by_plate(plate)
            if not v:
                print(f"\n  未找到车牌号为 {plate} 的车辆")
                input("\n按回车继续...")
                continue
            confirm = input(f"  确认删除车辆 {plate}？(y/N): ").strip().lower()
            if confirm == 'y':
                VehicleService.delete_vehicle(v['id'])
                print("\n  车辆已删除")
            else:
                print("\n  已取消")
            input("\n按回车继续...")


# ========== 配件库存管理 ==========
def parts_menu():
    while True:
        print_header("配件库存管理")
        print_menu([
            "新增配件", "查看所有配件", "搜索配件", "配件入库", "配件出库",
            "查看库存预警", "查看采购建议", "配件出入库明细"
        ])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("新增配件")
            name = input_prompt("配件名称", required=True)
            code = input_prompt("配件编号", required=True)
            price = input_float("单价(元)", required=True, min_value=0)
            stock = input_int("初始库存数量", default=0)
            min_stock = input_int("最小库存量(预警阈值)", default=5)
            pid, err = PartService.add_part(name, code, price, stock, min_stock)
            if err:
                print(f"\n  错误: {err}")
            else:
                print(f"\n  配件创建成功，ID: {pid}")
            input("\n按回车继续...")

        elif choice == "2":
            print_header("所有配件列表")
            parts = PartService.list_parts()
            if not parts:
                print("  暂无配件数据")
            else:
                print(f"  {'ID':<6}{'编号':<10}{'名称':<16}{'单价(元)':<10}{'库存':<8}{'最小库存':<8}状态")
                print("  " + "-" * 64)
                for p in parts:
                    status = "⚠ 库存不足" if p['stock'] < p['min_stock'] else "✓ 正常"
                    print(f"  {p['id']:<6}{p['code']:<10}{p['name']:<16}"
                          f"{p['price']:<10.2f}{p['stock']:<8}{p['min_stock']:<8}{status}")
            input("\n按回车继续...")

        elif choice == "3":
            print_header("搜索配件")
            kw = input_prompt("请输入关键词(名称/编号)", required=True)
            parts = PartService.search_parts(kw)
            if not parts:
                print("  未找到匹配的配件")
            else:
                print(f"  {'ID':<6}{'编号':<10}{'名称':<16}{'单价(元)':<10}{'库存':<8}")
                print("  " + "-" * 54)
                for p in parts:
                    print(f"  {p['id']:<6}{p['code']:<10}{p['name']:<16}"
                          f"{p['price']:<10.2f}{p['stock']}")
            input("\n按回车继续...")

        elif choice == "4":
            print_header("配件入库")
            code = input_prompt("请输入配件编号", required=True)
            part = PartService.find_part_by_code(code)
            if not part:
                print(f"\n  未找到配件 {code}")
                input("\n按回车继续...")
                continue
            qty = input_int("入库数量", required=True, min_value=1)
            note = input_prompt("备注", default="采购入库")
            ok, err = PartService.stock_in(part['id'], qty, note)
            if err:
                print(f"\n  错误: {err}")
            else:
                new_part = PartService.find_part_by_id(part['id'])
                print(f"\n  入库成功，当前库存: {new_part['stock']}")
            input("\n按回车继续...")

        elif choice == "5":
            print_header("配件出库")
            code = input_prompt("请输入配件编号", required=True)
            part = PartService.find_part_by_code(code)
            if not part:
                print(f"\n  未找到配件 {code}")
                input("\n按回车继续...")
                continue
            print(f"  当前库存: {part['stock']}")
            qty = input_int("出库数量", required=True, min_value=1)
            ok, err = PartService.stock_out(part['id'], qty)
            if err:
                print(f"\n  错误: {err}")
            else:
                new_part = PartService.find_part_by_id(part['id'])
                print(f"\n  出库成功，当前库存: {new_part['stock']}")
                if new_part['stock'] < new_part['min_stock']:
                    print(f"  ⚠ 警告: 当前库存已低于最小库存阈值({new_part['min_stock']})，建议补货")
            input("\n按回车继续...")

        elif choice == "6":
            print_header("库存预警")
            low = PartService.get_low_stock_parts()
            if not low:
                print("  当前无库存不足的配件")
            else:
                print(f"  {'编号':<10}{'名称':<16}{'当前库存':<10}{'最小库存':<10}缺口")
                print("  " + "-" * 52)
                for p in low:
                    gap = p['min_stock'] - p['stock']
                    print(f"  {p['code']:<10}{p['name']:<16}{p['stock']:<10}{p['min_stock']:<10}{gap}")
            input("\n按回车继续...")

        elif choice == "7":
            print_header("采购建议")
            suggestions = PurchaseSuggestionService.generate_all_suggestions()
            if not suggestions:
                print("  当前无待处理的采购建议")
            else:
                print(f"  {'ID':<6}{'配件名称':<16}{'当前库存':<10}{'建议采购量':<10}创建时间")
                print("  " + "-" * 58)
                for s in suggestions:
                    print(f"  {s['id']:<6}{s['part_name']:<16}{s['current_stock']:<10}"
                          f"{s['suggested_quantity']:<10}{s['created_at']}")
            input("\n按回车继续...")

        elif choice == "8":
            print_header("配件出入库明细")
            print("  1. 查询全部记录")
            print("  2. 按日期范围查询")
            sub = input("\n请选择: ").strip()
            start_date = end_date = None
            if sub == "2":
                start_date = input_prompt("开始日期(YYYY-MM-DD)", required=True)
                end_date = input_prompt("结束日期(YYYY-MM-DD)", required=True)
            transactions = PartService.list_transactions(start_date, end_date)
            if not transactions:
                print("  暂无出入库记录")
            else:
                print(f"  {'日期时间':<20}{'编号':<10}{'名称':<16}{'类型':<6}{'数量':<6}备注")
                print("  " + "-" * 64)
                for t in transactions:
                    t_type = "入库" if t['type'] == 'IN' else "出库"
                    print(f"  {t['created_at']:<20}{t.get('part_code',''):<10}"
                          f"{t.get('part_name',''):<16}{t_type:<6}{t['quantity']:<6}"
                          f"{t.get('note','') or ''}")
            input("\n按回车继续...")


# ========== 故障码管理 ==========
def fault_code_menu():
    while True:
        print_header("常用故障码管理")
        print_menu(["新增故障码", "查看所有故障码", "搜索故障码", "修改故障码", "删除故障码"])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("新增故障码")
            code = input_prompt("故障码(如P0300)", required=True)
            desc = input_prompt("故障描述", required=True)
            solution = input_prompt("处理方案", required=True)
            fid, err = FaultCodeService.add_fault_code(code, desc, solution)
            if err:
                print(f"\n  错误: {err}")
            else:
                print(f"\n  故障码创建成功，ID: {fid}")
            input("\n按回车继续...")

        elif choice == "2":
            print_header("所有故障码")
            codes = FaultCodeService.list_fault_codes()
            if not codes:
                print("  暂无故障码数据")
            else:
                for fc in codes:
                    print(f"\n  [{fc['code']}] {fc['description']}")
                    print(f"    处理方案: {fc['solution']}")
            input("\n按回车继续...")

        elif choice == "3":
            print_header("搜索故障码")
            kw = input_prompt("请输入关键词(故障码/描述)", required=True)
            codes = FaultCodeService.search_fault_codes(kw)
            if not codes:
                print("  未找到匹配的故障码")
            else:
                for fc in codes:
                    print(f"\n  [{fc['code']}] {fc['description']}")
                    print(f"    处理方案: {fc['solution']}")
            input("\n按回车继续...")

        elif choice == "4":
            print_header("修改故障码")
            code_val = input_prompt("请输入故障码", required=True)
            fc = FaultCodeService.find_by_code(code_val)
            if not fc:
                print(f"\n  未找到故障码 {code_val}")
                input("\n按回车继续...")
                continue
            desc = input_prompt("故障描述", default=fc['description'])
            solution = input_prompt("处理方案", default=fc['solution'])
            FaultCodeService.update_fault_code(fc['id'], description=desc, solution=solution)
            print("\n  故障码已更新")
            input("\n按回车继续...")

        elif choice == "5":
            print_header("删除故障码")
            code_val = input_prompt("请输入故障码", required=True)
            fc = FaultCodeService.find_by_code(code_val)
            if not fc:
                print(f"\n  未找到故障码 {code_val}")
                input("\n按回车继续...")
                continue
            confirm = input(f"  确认删除故障码 {code_val}？(y/N): ").strip().lower()
            if confirm == 'y':
                FaultCodeService.delete_fault_code(fc['id'])
                print("\n  故障码已删除")
            else:
                print("\n  已取消")
            input("\n按回车继续...")


# ========== 工单管理 ==========
def select_parts_for_order():
    selected_parts = []
    while True:
        print(f"\n  已选配件: {len(selected_parts)} 项")
        if selected_parts:
            for i, sp in enumerate(selected_parts, 1):
                p = PartService.find_part_by_id(sp['part_id'])
                print(f"    {i}. {p['name']}({p['code']}) - {sp['quantity']}件 - ¥{p['price'] * sp['quantity']:.2f}")
        print("\n  1. 添加配件")
        print("  2. 删除已选配件")
        print("  0. 确认完成")
        sub = input("\n  请选择: ").strip()

        if sub == "0":
            break
        elif sub == "1":
            kw = input_prompt("  搜索配件(名称/编号)", required=True)
            parts = PartService.search_parts(kw)
            if not parts:
                print("    未找到匹配的配件")
                continue
            print(f"\n    {'序号':<6}{'编号':<10}{'名称':<16}{'单价(元)':<10}{'库存'}")
            print("    " + "-" * 52)
            for i, p in enumerate(parts, 1):
                print(f"    {i:<6}{p['code']:<10}{p['name']:<16}{p['price']:<10.2f}{p['stock']}")
            idx = input_int("  选择序号", required=True, min_value=1) - 1
            if idx < 0 or idx >= len(parts):
                print("  无效的序号")
                continue
            selected = parts[idx]
            qty = input_int("  数量", required=True, min_value=1)
            if qty > selected['stock']:
                print(f"  库存不足，当前库存: {selected['stock']}")
                continue
            selected_parts.append({'part_id': selected['id'], 'quantity': qty})
            print(f"  已添加: {selected['name']} x{qty}")

        elif sub == "2":
            if not selected_parts:
                print("  当前未选择任何配件")
                continue
            idx = input_int("  输入要删除的序号", required=True, min_value=1) - 1
            if 0 <= idx < len(selected_parts):
                removed = selected_parts.pop(idx)
                p = PartService.find_part_by_id(removed['part_id'])
                print(f"  已删除: {p['name']}")
            else:
                print("  无效的序号")
    return selected_parts


def work_order_menu():
    while True:
        print_header("维修工单管理")
        print_menu(["创建工单", "查看所有工单", "查看工单详情", "查询车辆维修历史"])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("创建维修工单")
            plate = input_prompt("车牌号", required=True)
            vehicle = VehicleService.find_vehicle_by_plate(plate)
            if not vehicle:
                print(f"\n  未找到车辆 {plate}，请先创建车辆档案")
                input("\n按回车继续...")
                continue
            mileage = input_int("进厂里程(km)", required=True, min_value=0)
            fault_desc = input_prompt("故障描述", required=True)

            use_fc = input("  是否引用故障码？(y/N): ").strip().lower()
            fault_code_id = None
            if use_fc == 'y':
                kw = input_prompt("  搜索故障码", required=True)
                codes = FaultCodeService.search_fault_codes(kw)
                if codes:
                    for i, fc in enumerate(codes, 1):
                        print(f"    {i}. [{fc['code']}] {fc['description']}")
                    idx = input_int("  选择序号(0跳过)", default=0) - 1
                    if 0 <= idx < len(codes):
                        fault_code_id = codes[idx]['id']
                        print(f"  已引用故障码: {codes[idx]['code']}")
                        print(f"  处理方案: {codes[idx]['solution']}")
                        if not fault_desc:
                            fault_desc = codes[idx]['description']

            labor_cost = input_float("工时费(元)", default=0)
            print("\n  --- 添加更换配件 ---")
            parts = select_parts_for_order()

            result = WorkOrderService.create_work_order(
                vehicle['id'], mileage, fault_desc, fault_code_id, labor_cost, parts
            )
            print(f"\n  {'='*50}")
            print(f"  工单创建成功！工单号: {result['order_id']}")
            print(f"  配件数量: {result['parts_count']} 项")
            print(f"  总费用: ¥{result['total_cost']:.2f}")

            if result['maintenance_due']:
                print(f"\n  ⚠ 提醒: 该车已到保养周期！")
                print(f"     (距离上次保养已行驶 {result['mileage_since_last']} km，周期{MAINTENANCE_INTERVAL}km)")
                update_last = input("\n  是否更新上次保养里程为当前里程？(Y/n): ").strip().lower()
                if update_last in ('', 'y'):
                    VehicleService.update_last_mileage(vehicle['id'], mileage)
                    print(f"  已更新上次保养里程为 {mileage} km")
            print(f"  {'='*50}")
            input("\n按回车继续...")

        elif choice == "2":
            print_header("所有工单列表")
            orders = WorkOrderService.list_work_orders()
            if not orders:
                print("  暂无工单")
            else:
                print(f"  {'工单号':<8}{'日期':<20}{'车牌号':<12}{'里程(km)':<12}{'总费用(元)':<12}故障描述")
                print("  " + "-" * 72)
                for o in orders:
                    desc = o['fault_description'][:20] + '...' if len(o['fault_description']) > 20 else o['fault_description']
                    print(f"  {o['id']:<8}{o['created_at']:<20}{o.get('plate_number',''):<12}"
                          f"{o['mileage']:<12}{o['total_cost']:<12.2f}{desc}")
            input("\n按回车继续...")

        elif choice == "3":
            print_header("工单详情")
            oid = input_int("请输入工单号", required=True, min_value=1)
            order = WorkOrderService.get_work_order_detail(oid)
            if not order:
                print(f"\n  未找到工单号 {oid}")
                input("\n按回车继续...")
                continue
            print(f"\n  工单号:       {order['id']}")
            print(f"  创建时间:     {order['created_at']}")
            print(f"  车牌号:       {order.get('plate_number', '')}")
            print(f"  品牌型号:     {order.get('brand_model', '')}")
            print(f"  进厂里程:     {order['mileage']} km")
            print(f"  故障描述:     {order['fault_description']}")
            if order.get('fault_code'):
                print(f"  故障码:       {order['fault_code']} - {order.get('fault_desc','')}")
                print(f"  处理方案:     {order.get('fault_solution','')}")
            print()

            parts = order['parts']
            if parts:
                print(f"  更换配件:")
                print(f"  {'序号':<6}{'名称':<16}{'编号':<10}{'单价(元)':<10}{'数量':<6}{'小计(元)':<10}")
                print("  " + "-" * 58)
                parts_total = 0
                for i, p in enumerate(parts, 1):
                    parts_total += p['subtotal']
                    print(f"  {i:<6}{p['part_name']:<16}{p['part_code']:<10}"
                          f"{p['unit_price']:<10.2f}{p['quantity']:<6}{p['subtotal']:<10.2f}")
                print(f"\n  配件小计:     {parts_total:.2f} 元")
            print(f"  工时费:       {order['labor_cost']:.2f} 元")
            print(f"  工单总计:     {order['total_cost']:.2f} 元")
            input("\n按回车继续...")

        elif choice == "4":
            print_header("查询车辆维修历史")
            plate = input_prompt("请输入车牌号", required=True)
            report = generate_history_report(plate)
            if not report:
                print(f"\n  未找到车牌号为 {plate} 的车辆或维修记录")
                input("\n按回车继续...")
                continue
            print()
            print(report)
            save = input("\n  是否保存为文本报告？(y/N): ").strip().lower()
            if save == 'y':
                ok, path = save_history_report(plate)
                if ok:
                    print(f"  报告已保存至: {path}")
                else:
                    print(f"  保存失败: {path}")
            input("\n按回车继续...")


# ========== 报表导出 ==========
def reports_menu():
    while True:
        print_header("报表与导出")
        print_menu([
            "导出配件出入库明细(Excel)",
            "导出维修收入统计报表(Excel)",
            "生成车辆维修历史报告(文本)"
        ])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("导出配件出入库明细")
            print("  1. 导出全部")
            print("  2. 按日期范围导出")
            sub = input("\n请选择: ").strip()
            start_date = end_date = None
            if sub == "2":
                start_date = input_prompt("开始日期(YYYY-MM-DD)", required=True)
                end_date = input_prompt("结束日期(YYYY-MM-DD)", required=True)
            ok, result = export_parts_transactions(start_date, end_date)
            if ok:
                print(f"\n  导出成功！文件路径: {result}")
            else:
                print(f"\n  导出失败: {result}")
            input("\n按回车继续...")

        elif choice == "2":
            print_header("导出维修收入统计报表")
            start_date = input_prompt("开始日期(YYYY-MM-DD)", required=True)
            end_date = input_prompt("结束日期(YYYY-MM-DD)", required=True)
            ok, result = export_revenue_report(start_date, end_date)
            if ok:
                print(f"\n  导出成功！文件路径: {result}")
            else:
                print(f"\n  导出失败: {result}")
            input("\n按回车继续...")

        elif choice == "3":
            print_header("生成车辆维修历史报告")
            plate = input_prompt("请输入车牌号", required=True)
            ok, result = save_history_report(plate)
            if ok:
                print(f"\n  导出成功！文件路径: {result}")
                preview = input("\n  是否在屏幕上预览？(Y/n): ").strip().lower()
                if preview in ('', 'y'):
                    report = generate_history_report(plate)
                    if report:
                        print()
                        print(report)
            else:
                print(f"\n  导出失败: {result}")
            input("\n按回车继续...")


# ========== 主菜单 ==========
def main_menu():
    while True:
        width = 60
        print()
        print("=" * width)
        print("🚗 汽车维修保养记录与配件库存管理系统".center(width))
        print("=" * width)
        print()
        print("  1. 车辆档案管理")
        print("  2. 配件库存管理")
        print("  3. 常用故障码管理")
        print("  4. 维修工单管理")
        print("  5. 报表与导出")
        print("  0. 退出系统")
        print()
        choice = input("请选择功能模块: ").strip()

        if choice == "0":
            print("\n  感谢使用，再见！")
            sys.exit(0)
        elif choice == "1":
            vehicle_menu()
        elif choice == "2":
            parts_menu()
        elif choice == "3":
            fault_code_menu()
        elif choice == "4":
            work_order_menu()
        elif choice == "5":
            reports_menu()
        else:
            print("  无效的选择，请重新输入。")
            input("\n按回车继续...")


def main():
    init_db()
    seed_sample_data()
    print("\n  系统初始化完成！")
    print(f"  保养周期: 每 {MAINTENANCE_INTERVAL} 公里")
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n  感谢使用，再见！")
        sys.exit(0)


if __name__ == "__main__":
    main()
