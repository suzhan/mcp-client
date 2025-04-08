import uvicorn
import os
import sys
import logging
from pathlib import Path

# 配置基本日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp_client.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        # 获取并打印当前工作目录
        current_dir = os.getcwd()
        logger.info(f"当前工作目录: {current_dir}")
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        logger.info(f"项目根目录: {project_root}")
        
        # 确保当前工作目录是项目根目录
        os.chdir(project_root)
        logger.info(f"已切换工作目录到: {os.getcwd()}")
        
        # 检查app目录是否存在
        app_dir = project_root / "app"
        if not app_dir.exists():
            logger.error(f"app目录不存在: {app_dir}")
            sys.exit(1)
        logger.info(f"app目录存在: {app_dir}")
        
        # 检查main.py是否存在
        main_file = app_dir / "main.py"
        if not main_file.exists():
            logger.error(f"main.py不存在: {main_file}")
            sys.exit(1)
        logger.info(f"main.py文件存在: {main_file}")
        
        # 打印Python路径
        logger.info(f"Python路径: {sys.path}")
        
        # 运行应用
        logger.info("正在启动FastAPI应用...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_level="info"
        )
    except Exception as e:
        logger.error(f"启动失败: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 