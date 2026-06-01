from typing import Any, Dict

from app.agents.output_agents.markdown_agent.summary_agent import MarkdownSummaryAgent
from app.agents.output_agents.requirement_spec_agent.agent import RequirementSpecOutputAgent
from app.agents.output_agents.screen_plan_agent.agent import ScreenPlanOutputAgent
from app.agents.output_agents.wbs_output_agent.agent import WBSOutputAgent
from app.storage.file_version import next_versioned_output_path
from app.core.pm_logger import log_info, log_step


class OutputOrchestrator:
    """process.json의 output_agents enabled 설정에 따라 산출물을 생성한다."""

    def __init__(self, process: Dict[str, Any], mapper: Dict[str, Any]):
        self.process = process
        self.mapper = mapper

    def _enabled_outputs(self) -> Dict[str, Dict[str, Any]]:
        outputs = self.process.get('output_agents', {})
        return {key: value for key, value in outputs.items() if bool(value.get('enabled', False))}

    def run(self, core_data: Dict[str, Any], output_dir: str, project_name: str, author: str) -> Dict[str, str]:
        generated: Dict[str, str] = {}
        for output_key, output_cfg in self._enabled_outputs().items():
            if output_key == 'requirement_spec':
                log_step('[8] Requirement Spec Output Agent 실행')
                output_path = next_versioned_output_path(output_dir, project_name, output_key, self.mapper, '.xlsx')
                section = self.mapper.get('requirement_spec', {})
                RequirementSpecOutputAgent().run(
                    atoms=core_data.get('requirements', []),
                    template_path=section.get('template_path', ''),
                    output_path=output_path,
                    project_name=project_name,
                    author=author,
                    mapper=section,
                )
                generated[output_key] = output_path

            elif output_key == 'wbs':
                log_step('[9] WBS Output Agent 실행')
                output_path = next_versioned_output_path(output_dir, project_name, output_key, self.mapper, '.xlsx')
                section = self.mapper.get('wbs', {})
                WBSOutputAgent().run(
                    items=core_data.get('wbs_items', []),
                    template_path=section.get('template_path', ''),
                    output_path=output_path,
                    mapper=section,
                )
                generated[output_key] = output_path

            elif output_key == 'screen_plan':
                log_step('[10] Screen Plan Output Agent 실행')
                output_path = next_versioned_output_path(output_dir, project_name, output_key, self.mapper, '.pptx')
                section = self.mapper.get('screen_plan', {})
                ScreenPlanOutputAgent().run(
                    items=core_data.get('screen_items', []),
                    template_path=section.get('template_path', ''),
                    output_path=output_path,
                    project_name=project_name,
                    author=author,
                    mapper=section,
                )
                generated[output_key] = output_path

            elif output_key == 'markdown_summary':
                log_step('[11] Markdown Agent 실행')
                doc_name = output_cfg.get('document_name', '분석요약')
                extension = output_cfg.get('extension', '.md')
                mapper = dict(self.mapper)
                mapper.setdefault('output_files', {}).setdefault('documents', {})[output_key] = {
                    'document_name': doc_name,
                    'extension': extension,
                }
                output_path = next_versioned_output_path(output_dir, project_name, output_key, mapper, extension)
                MarkdownSummaryAgent().run(output_path=output_path, project_name=project_name, core_data=core_data)
                generated[output_key] = output_path

        log_step('[완료] 산출물 생성 완료')
        for path in generated.values():
            log_info(f'- {path}')
        return generated
