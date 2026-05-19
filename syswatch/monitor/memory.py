
import psutil


class MemoryMonitor:
    def snapshot(self) -> dict:
        vm  = psutil.virtual_memory()
        sw  = psutil.swap_memory()
        return {
            "total":        vm.total,
            "used":         vm.used,
            "available":    vm.available,
            "percent":      vm.percent,
            "cached":       getattr(vm, "cached", 0),
            "swap_total":   sw.total,
            "swap_used":    sw.used,
            "swap_percent": sw.percent,
        }
