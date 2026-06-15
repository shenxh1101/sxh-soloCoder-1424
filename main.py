import sys
from database import init_db, seed_sample_data, MAINTENANCE_INTERVAL, migrate_db
from services import (
    VehicleService, PartService, FaultCodeService,
    WorkOrderService, PurchaseSuggestionService
)
from reports import (
    export_parts_transactions, export_revenue_report,
    generate_history_report, save_history_report,
    export_parts_template, export_parts_list, import_parts_from_excel
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


def input_float(prompt, default=None, required=False, min_value=None):
    while True:
        val = input_prompt(prompt, default, required)
        if val == "" and not required:
            return 0.0
        try:
            num = float(val)
            if min_value is not None and num < min_value:
                print(f"  请输入大于等于 {min_value} 的数字。")
                continue
            return num
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
        print_menu([
            "新增车辆档案", "查看所有车辆", "按车牌号查询",
            "车辆维修概览(快速视图)", "修改车辆信息", "删除车辆"
        ])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("新增车辆档案")
            while True:
                try:
                    plate = input_prompt("车牌号", required=True)
                    brand = input_prompt("品牌型号", required=True)
                    vin = input_prompt("VIN码", required=True)
                    mileage = input_int("上次保养里程(km)", default=0)
                    vid, err = VehicleService.add_vehicle(plate, brand, vin, mileage)
                    if err:
                        print(f"\n  ✗ 错误: {err}")
                        retry = input("  是否重新输入？(Y/n): ").strip().lower()
                        if retry == 'n':
                            break
                        print()
                        continue
                    print(f"\n  ✓ 车辆档案创建成功，ID: {vid}")
                    break
                except Exception as e:
                    print(f"\n  ✗ 操作失败: {str(e)}")
                    retry = input("  是否重新输入？(Y/n): ").strip().lower()
                    if retry == 'n':
                        break
                    print()
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
            print_header("车辆维修概览")
            plate = input_prompt("请输入车牌号", required=True)
            try:
                ok, result = WorkOrderService.get_vehicle_overview(plate)
                if not ok:
                    print(f"\n  ✗ {result}")
                    input("\n按回车继续...")
                    continue
                v = result['vehicle']
                print()
                print(f"  ┌{'─' * 56}┐")
                print(f"  │  {'车辆信息':<18}{' ':>34}│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  车牌号: {v['plate_number']:<20}品牌: {v['brand_model']:<16}│")
                print(f"  │  VIN码:  {v['vin_code']:<40}│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  {'维修统计':<18}{' ':>34}│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  累计维修: {result['order_count']:<4}次    累计花费: ¥{result['total_spent']:<10}│")
                if result['void_count'] > 0:
                    print(f"  │  撤销工单: {result['void_count']:<4}次{' ':>36}│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  {'保养状态':<18}{' ':>34}│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  当前里程: {result['latest_mileage']:<5}km   上次保养: {v['last_maintenance_mileage']:<5}km│")
                diff = result['mileage_since_maintenance']
                if result['maintenance_due']:
                    print(f"  │  ⚠ 已超保养周期 {diff - MAINTENANCE_INTERVAL} km，建议立即保养！│")
                else:
                    print(f"  │  已行驶 {diff:<5}km   剩余 {result['maintenance_remaining']:<5}km 到保养│")
                print(f"  ├{'─' * 56}┤")
                print(f"  │  最近 {len(result['recent_orders'])} 次维修记录:{' ':>28}│")
                print(f"  ├{'─' * 56}┤")
                if not result['recent_orders']:
                    print(f"  │  暂无维修记录{' ':>42}│")
                else:
                    for o in result['recent_orders']:
                        desc = o['fault_description'][:16]
                        print(f"  │  {o['created_at'][:10]} {desc:<14}¥{o['total_cost']:<8}│")
                print(f"  └{'─' * 56}┘")
            except Exception as e:
                print(f"\n  ✗ 概览生成失败: {str(e)}")
            input("\n按回车继续...")

        elif choice == "5":
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

        elif choice == "6":
            print_header("删除车辆")
            try:
                plate = input_prompt("请输入车牌号", required=True)
                v = VehicleService.find_vehicle_by_plate(plate)
                if not v:
                    print(f"\n  ✗ 未找到车牌号为 {plate} 的车辆")
                    input("\n按回车继续...")
                    continue

                order_count = VehicleService.get_work_order_count(v['id'])
                if order_count > 0:
                    print(f"\n  ⚠  该车辆存在 {order_count} 条维修记录")
                    print("  直接删除将同时删除所有关联的工单、配件领用记录")
                    confirm = input(f"  确认级联删除车辆 {plate} 及其所有维修记录？(y/N): ").strip().lower()
                    if confirm == 'y':
                        ok, err = VehicleService.delete_vehicle(v['id'], cascade=True)
                        if ok:
                            print(f"\n  ✓ 车辆及关联的 {order_count} 条维修记录已删除")
                        else:
                            print(f"\n  ✗ 删除失败: {err}")
                    else:
                        print("\n  已取消删除")
                else:
                    confirm = input(f"  确认删除车辆 {plate}？(y/N): ").strip().lower()
                    if confirm == 'y':
                        ok, err = VehicleService.delete_vehicle(v['id'])
                        if ok:
                            print("\n  ✓ 车辆已删除")
                        else:
                            print(f"\n  ✗ 删除失败: {err}")
                    else:
                        print("\n  已取消删除")
            except Exception as e:
                print(f"\n  ✗ 操作失败: {str(e)}")
            input("\n按回车继续...")


# ========== 配件库存管理 ==========
def parts_menu():
    while True:
        print_header("配件库存管理")
        print_menu([
            "新增配件", "查看所有配件", "搜索配件", "配件入库", "配件出库",
            "查看库存预警", "处理采购建议", "配件出入库明细",
            "批量导入配件", "导出配件清单", "生成导入模板"
        ])
        choice = input("请选择操作: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print_header("新增配件")
            try:
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
                    if stock > 0:
                        print(f"  当前库存: {stock}")
            except Exception as e:
                print(f"\n  操作失败: {str(e)}")
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
            while True:
                print_header("采购建议管理")
                try:
                    stats = PurchaseSuggestionService.get_suggestion_statistics()
                    print(f"  📊 统计概览: 待处理{stats['pending_count']} | 已处理{stats['processed_count']} | 已忽略{stats['ignored_count']}")
                    print(f"           缺件{stats['pending_parts_count']}种 | 待采购{stats['total_pending_qty']}件 | 预估金额¥{stats['total_suggested_value']}")
                except Exception:
                    pass
                print()
                print("  1. 查看待处理采购建议")
                print("  2. 处理单条采购建议(入库)")
                print("  3. 标记采购建议为忽略")
                print("  4. 查看全部采购建议(含历史)")
                print("  5. 重新生成采购建议(扫一遍库存)")
                print("  0. 返回配件管理菜单")
                sub = input("\n请选择: ").strip()

                if sub == "0":
                    break
                elif sub == "1":
                    suggestions = PurchaseSuggestionService.list_suggestions('PENDING')
                    if not suggestions:
                        print("\n  当前无待处理的采购建议")
                    else:
                        print(f"\n  {'ID':<6}{'配件名称':<16}{'当前库存':<10}{'建议量':<8}{'缺口':<8}创建时间")
                        print("  " + "-" * 62)
                        for s in suggestions:
                            gap = max(0, 5 - s['current_stock'])
                            print(f"  {s['id']:<6}{s['part_name']:<16}{s['current_stock']:<10}"
                                  f"{s['suggested_quantity']:<8}{gap:<8}{s['created_at']}")
                    input("\n按回车继续...")

                elif sub == "2":
                    suggestions = PurchaseSuggestionService.list_suggestions('PENDING')
                    if not suggestions:
                        print("\n  当前无待处理的采购建议")
                        input("\n按回车继续...")
                        continue
                    print(f"\n  {'ID':<6}{'配件名称':<16}{'当前库存':<10}{'建议采购量':<12}")
                    print("  " + "-" * 46)
                    for s in suggestions:
                        print(f"  {s['id']:<6}{s['part_name']:<16}{s['current_stock']:<10}{s['suggested_quantity']:<12}")
                    ps_id = input_int("\n请输入要处理的采购建议ID", required=True, min_value=1)
                    ps_item = next((s for s in suggestions if s['id'] == ps_id), None)
                    default_qty = ps_item['suggested_quantity'] if ps_item else None
                    qty = input_int("实际采购入库数量", default=default_qty, required=True, min_value=1)
                    ok, res = PurchaseSuggestionService.mark_processed(ps_id, qty)
                    if ok:
                        print(f"\n  ✓ 处理成功: {res['part_name']}({res['part_code']})")
                        print(f"    采购入库: {res['purchased_qty']}件，新库存: {res['new_stock']}件")
                    else:
                        print(f"\n  ✗ 处理失败: {res}")
                    input("\n按回车继续...")

                elif sub == "3":
                    suggestions = PurchaseSuggestionService.list_suggestions('PENDING')
                    if not suggestions:
                        print("\n  当前无待处理的采购建议")
                        input("\n按回车继续...")
                        continue
                    ps_id = input_int("请输入要标记忽略的采购建议ID", required=True, min_value=1)
                    PurchaseSuggestionService.mark_ignored(ps_id)
                    print("\n  ✓ 已标记为忽略")
                    input("\n按回车继续...")

                elif sub == "4":
                    all_s = PurchaseSuggestionService.list_suggestions()
                    if not all_s:
                        print("\n  暂无采购建议记录")
                    else:
                        status_map = {'PENDING': '待处理', 'PROCESSED': '已处理', 'IGNORED': '已忽略'}
                        print(f"\n  {'ID':<6}{'配件名称':<16}{'建议量':<8}{'状态':<10}创建时间")
                        print("  " + "-" * 56)
                        for s in all_s:
                            st = status_map.get(s['status'], s['status'])
                            print(f"  {s['id']:<6}{s['part_name']:<16}{s['suggested_quantity']:<8}{st:<10}{s['created_at']}")
                    input("\n按回车继续...")

                elif sub == "5":
                    suggestions = PurchaseSuggestionService.generate_all_suggestions()
                    print(f"\n  ✓ 扫描完成，生成/保留待处理建议 {len(suggestions)} 条")
                    if suggestions:
                        for s in suggestions:
                            print(f"    - {s['part_name']}: 库存{s['current_stock']}件，建议采购{s['suggested_quantity']}件")
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

        elif choice == "9":
            print_header("批量导入配件")
            print("  提示: 请先选择[生成导入模板]获取Excel格式模板")
            fpath = input_prompt("请输入Excel文件完整路径", required=True).strip().strip('"')
            try:
                ok, err, success_list, failure_list = import_parts_from_excel(fpath)
                if not ok:
                    print(f"\n  ✗ 导入失败: {err}")
                    input("\n按回车继续...")
                    continue
                print(f"\n  {'=' * 58}")
                print(f"  导入完成: 共 {len(success_list) + len(failure_list)} 条, 成功 {len(success_list)} 条, 失败 {len(failure_list)} 条")
                print(f"  {'=' * 58}")
                if success_list:
                    print(f"\n  ✓ 成功导入的配件 ({len(success_list)} 条):")
                    print(f"  {'行号':<6}{'ID':<6}{'编号':<12}{'名称':<18}{'单价':<10}{'库存'}")
                    print("  " + "-" * 60)
                    for s in success_list:
                        print(f"  {s['row']:<6}{s['id']:<6}{s['code']:<12}{s['name']:<18}{s['price']:<10.2f}{s['stock']}")
                if failure_list:
                    print(f"\n  ✗ 导入失败的配件 ({len(failure_list)} 条):")
                    for f in failure_list:
                        print(f"    第{f['row']}行 [{f.get('code','空') or '空'}-{f.get('name','')}]: {'; '.join(f['errors'])}")
            except Exception as e:
                print(f"\n  ✗ 导入异常: {str(e)}")
            input("\n按回车继续...")

        elif choice == "10":
            print_header("导出配件清单")
            ok, res = export_parts_list()
            if ok:
                print(f"\n  ✓ 导出成功! 文件路径: {res}")
            else:
                print(f"\n  ✗ 导出失败: {res}")
            input("\n按回车继续...")

        elif choice == "11":
            print_header("生成配件导入模板")
            ok, res = export_parts_template()
            if ok:
                print(f"\n  ✓ 模板生成成功! 文件路径: {res}")
                print(f"  请用Excel打开编辑，填写后使用[批量导入配件]功能导入")
            else:
                print(f"\n  ✗ 生成失败: {res}")
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

            existing_idx = -1
            for i, sp in enumerate(selected_parts):
                if sp['part_id'] == selected['id']:
                    existing_idx = i
                    break

            if existing_idx >= 0:
                current_qty = selected_parts[existing_idx]['quantity']
                new_qty = current_qty + qty
                if new_qty > selected['stock']:
                    print(f"  库存不足，已选{current_qty}件，再加{qty}件共{new_qty}件超过库存{selected['stock']}件")
                    continue
                selected_parts[existing_idx]['quantity'] = new_qty
                print(f"  已更新: {selected['name']} 共 {new_qty}件")
            else:
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
        print_menu([
            "创建工单", "查看所有工单", "查看工单详情",
            "撤销工单(回滚库存/金额)", "重新结算工单",
            "查询车辆维修历史"
        ])
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
            status_map = {'NORMAL': '正常', 'VOID': '已撤销'}
            st = status_map.get(order.get('status', 'NORMAL'), order.get('status', ''))
            print(f"\n  工单号:       {order['id']}")
            print(f"  状态:         {st}")
            print(f"  创建时间:     {order['created_at']}")
            if order.get('updated_at'):
                print(f"  最后更新:     {order['updated_at']}")
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
            print_header("撤销工单")
            oid = input_int("请输入要撤销的工单号", required=True, min_value=1)
            try:
                order = WorkOrderService.get_work_order_detail(oid)
                if not order:
                    print(f"\n  ✗ 未找到工单号 {oid}")
                    input("\n按回车继续...")
                    continue
                status_map = {'NORMAL': '正常', 'VOID': '已撤销'}
                st = status_map.get(order.get('status', 'NORMAL'), order.get('status', ''))
                print(f"\n  工单 #{oid} 信息:")
                print(f"    车牌号: {order.get('plate_number', '')} | 总金额: ¥{order['total_cost']:.2f}")
                print(f"    当前状态: {st}")
                print(f"    配件数: {len(order['parts'])} 项")

                confirm = input(f"\n  ⚠ 撤销后库存将回滚、维修历史将排除该工单，确认撤销？(y/N): ").strip().lower()
                if confirm != 'y':
                    print("\n  已取消")
                    input("\n按回车继续...")
                    continue

                ok, res = WorkOrderService.cancel_work_order(oid)
                if ok:
                    print(f"\n  ✓ 工单撤销成功！")
                    print(f"    返还配件数量: {res['returned_stock']} 件")
                    print(f"    冲销总金额: ¥{res['refund_amount']:.2f}")
                    print(f"    工单状态已标记为: 已撤销")
                else:
                    print(f"\n  ✗ 撤销失败: {res}")
            except Exception as e:
                print(f"\n  ✗ 操作异常: {str(e)}")
            input("\n按回车继续...")

        elif choice == "5":
            print_header("重新结算工单")
            oid = input_int("请输入要重新结算的工单号", required=True, min_value=1)
            try:
                order = WorkOrderService.get_work_order_detail(oid)
                if not order:
                    print(f"\n  ✗ 未找到工单号 {oid}")
                    input("\n按回车继续...")
                    continue
                if order.get('status') == 'VOID':
                    print(f"\n  ✗ 该工单已撤销，无法重新结算")
                    input("\n按回车继续...")
                    continue

                print(f"\n  当前工单 #{oid}:")
                print(f"    车牌号: {order.get('plate_number','')} | 里程: {order['mileage']} km")
                print(f"    原故障描述: {order['fault_description']}")
                print(f"    原总金额: ¥{order['total_cost']:.2f} (配件¥{sum(p['subtotal'] for p in order['parts']):.2f} + 工时¥{order['labor_cost']:.2f})")

                print()
                keep_desc = input("  保留原故障描述？(Y/n): ").strip().lower()
                new_desc = None
                if keep_desc != 'y' and keep_desc != '':
                    new_desc = input_prompt("  新故障描述", required=True)

                new_fc_id = None
                use_fc = input("  是否重新选择故障码？(y/N): ").strip().lower()
                if use_fc == 'y':
                    kw = input_prompt("  搜索故障码", required=True)
                    codes = FaultCodeService.search_fault_codes(kw)
                    if codes:
                        for i, fc in enumerate(codes, 1):
                            print(f"    {i}. [{fc['code']}] {fc['description']}")
                        idx = input_int("  选择序号(0为清空)", default=0) - 1
                        if idx >= 0 and idx < len(codes):
                            new_fc_id = codes[idx]['id']
                            if not new_desc:
                                new_desc = codes[idx]['description']

                new_labor = None
                keep_labor = input("  保留原工时费？(Y/n): ").strip().lower()
                if keep_labor != 'y' and keep_labor != '':
                    new_labor = input_float("  新工时费(元)", required=True, min_value=0)

                print(f"\n  --- 重新选择配件（原配件将全部回退库存后重新扣减）---")
                print("  原配件将先退库，再按新选择重新扣库，原配件可不保留")
                keep_parts = input("  保留原配件清单？(Y/n): ").strip().lower()
                if keep_parts == 'y' or keep_parts == '':
                    new_parts = [{'part_id': p['part_id'], 'quantity': p['quantity']} for p in order['parts']]
                    print(f"  已保留原配件 {len(new_parts)} 项，可在下方编辑")
                    while True:
                        print(f"\n  当前已选配件: {len(new_parts)} 项")
                        for i, np in enumerate(new_parts, 1):
                            p = PartService.find_part_by_id(np['part_id'])
                            print(f"    {i}. {p['name']}({p['code']}) x{np['quantity']}")
                        print("\n  1. 添加配件")
                        print("  2. 删除配件")
                        print("  3. 修改配件数量")
                        print("  0. 确认完成")
                        sub = input("\n  请选择: ").strip()
                        if sub == '0':
                            break
                        elif sub == '1':
                            kw = input_prompt("  搜索配件(名称/编号)", required=True)
                            parts = PartService.search_parts(kw)
                            if parts:
                                for i, p in enumerate(parts, 1):
                                    print(f"    {i}. {p['code']} {p['name']} ¥{p['price']:.2f} 库存{p['stock']}")
                                idx2 = input_int("  选择序号", required=True, min_value=1) - 1
                                if 0 <= idx2 < len(parts):
                                    sel = parts[idx2]
                                    qty = input_int("  数量", required=True, min_value=1)
                                    existing = next((x for x in new_parts if x['part_id'] == sel['id']), None)
                                    if existing:
                                        existing['quantity'] += qty
                                        print(f"  已更新: {sel['name']} 共{existing['quantity']}件")
                                    else:
                                        new_parts.append({'part_id': sel['id'], 'quantity': qty})
                                        print(f"  已添加: {sel['name']} x{qty}")
                        elif sub == '2':
                            if not new_parts:
                                print("  空")
                                continue
                            idx2 = input_int("  输入删除序号", required=True, min_value=1) - 1
                            if 0 <= idx2 < len(new_parts):
                                removed = new_parts.pop(idx2)
                                p = PartService.find_part_by_id(removed['part_id'])
                                print(f"  已删除: {p['name']}")
                        elif sub == '3':
                            if not new_parts:
                                print("  空")
                                continue
                            idx2 = input_int("  输入修改序号", required=True, min_value=1) - 1
                            if 0 <= idx2 < len(new_parts):
                                new_qty = input_int("  新数量", required=True, min_value=0)
                                if new_qty == 0:
                                    removed = new_parts.pop(idx2)
                                    p = PartService.find_part_by_id(removed['part_id'])
                                    print(f"  数量为0，已删除: {p['name']}")
                                else:
                                    new_parts[idx2]['quantity'] = new_qty
                                    print(f"  数量已更新为 {new_qty}")
                else:
                    print("\n  清空原配件，重新选择...")
                    new_parts = select_parts_for_order()

                confirm = input(f"\n  ⚠ 确认重新结算？原配件将退库后重新扣库。(y/N): ").strip().lower()
                if confirm != 'y':
                    print("\n  已取消")
                    input("\n按回车继续...")
                    continue

                ok, res = WorkOrderService.resettle_work_order(
                    oid, new_desc, new_fc_id, new_labor, new_parts
                )
                if ok:
                    print(f"\n  ✓ 工单重新结算成功！")
                    print(f"    原金额: ¥{res['old_total']:.2f} → 新金额: ¥{res['new_total']:.2f}")
                    diff = res['diff']
                    if diff > 0:
                        print(f"    差额: +¥{diff:.2f} (增加)")
                    elif diff < 0:
                        print(f"    差额: -¥{abs(diff):.2f} (减少)")
                    else:
                        print(f"    差额: ¥0.00 (不变)")
                    print(f"    配件项数: {res['parts_count']}")
                else:
                    print(f"\n  ✗ 重新结算失败: {res}")
            except Exception as e:
                print(f"\n  ✗ 操作异常: {str(e)}")
                import traceback
                traceback.print_exc()
            input("\n按回车继续...")

        elif choice == "6":
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
    migrate_db()
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
